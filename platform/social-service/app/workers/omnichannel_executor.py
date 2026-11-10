"""Fail-closed provider-backed executor for approved omnichannel actions.

Execution is opt-in. Only the adapters below can cause external side effects;
other platform/action combinations terminate as unsupported without a provider call.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import math
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.social_capabilities import SUPPORTED_PROVIDER_ACTIONS
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text

log = logging.getLogger(__name__)

POLL_SECONDS = 3
MAX_RATE_LIMIT_RETRIES = 3
SUPPORTED = SUPPORTED_PROVIDER_ACTIONS
TOKEN_PROVIDER = {"gmail": "google", "outlook": "microsoft", "x": "x", "linkedin": "linkedin"}
REQUIRED_SCOPES = {
    ("gmail", "send_message"): "https://www.googleapis.com/auth/gmail.send",
    ("outlook", "send_message"): "https://graph.microsoft.com/Mail.Send",
    ("x", "create_post"): "tweet.write",
    ("linkedin", "create_post"): "w_member_social",
}


def _fernet() -> Fernet:
    key = settings.provider_oauth_encryption_key
    if not key:
        raise RuntimeError("provider OAuth encryption is not configured")
    return Fernet(key.encode())


def _response_disposition(status_code: int) -> str:
    if status_code == 429:
        return "rate_limited"
    if status_code == 401:
        return "unauthorized"
    if status_code == 403:
        return "forbidden"
    if status_code >= 500:
        return "unknown"
    if status_code >= 400:
        return "rejected"
    return "success"


def _rate_limit_delay_seconds(retry_after: str | None, attempt: int) -> int:
    """Return a bounded retry delay, honoring Retry-After when it is valid."""
    fallback = min(15 * (2 ** max(attempt - 1, 0)), 300)
    if not retry_after:
        return fallback
    value = retry_after.strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            seconds = (retry_at - datetime.now(UTC)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return fallback
    if not math.isfinite(seconds):
        return fallback
    if seconds <= 0:
        return 1
    return min(int(seconds) + (1 if seconds % 1 else 0), 900)


def _approval_is_valid(action: dict[str, Any]) -> bool:
    payload = action.get("request_payload") or {}
    approval = payload.get("approval") or {}
    return (
        approval.get("approved") is True
        and bool(str(approval.get("approved_by") or "").strip())
        and str(approval.get("approved_by") or "") == str(payload.get("_requested_by") or "")
        and not str(approval.get("approved_by") or "").startswith(("n8n-", "automation-"))
        and bool(str(approval.get("approved_at") or "").strip())
        and (
            action.get("action") != "create_post"
            or approval.get("content_sha256") == hashlib.sha256(
                str(payload.get("text") or "").encode("utf-8")
            ).hexdigest()
        )
    )


def _provider_request(platform: str, action: str, token: str, account_id: str, payload: dict[str, Any]) -> tuple[str, str, dict[str, str], dict[str, Any]]:
    """Build only documented, narrowly-scoped requests; never log token/header data."""
    if (platform, action) not in SUPPORTED:
        raise ValueError("unsupported_action")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if platform == "gmail":
        to = str(payload.get("to") or "").strip()
        subject = str(payload.get("subject") or "").strip()
        body = str(payload.get("text") or "").strip()
        if not to or not subject or not body:
            raise ValueError("required_fields_missing")
        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
        return "POST", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send", headers, {"raw": raw}
    if platform == "outlook":
        to = str(payload.get("to") or "").strip()
        subject = str(payload.get("subject") or "").strip()
        body = str(payload.get("text") or "").strip()
        if not to or not subject or not body:
            raise ValueError("required_fields_missing")
        return "POST", "https://graph.microsoft.com/v1.0/me/sendMail", headers, {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}],
            },
            "saveToSentItems": True,
        }
    text_value = str(payload.get("text") or "").strip()
    if not text_value:
        raise ValueError("required_fields_missing")
    if platform == "x":
        return "POST", "https://api.x.com/2/tweets", headers, {"text": text_value}
    headers.update({"LinkedIn-Version": "202601", "X-Restli-Protocol-Version": "2.0.0"})
    # OAuth currently identifies a member account; organization posting requires
    # a separately verified organization grant and is intentionally unsupported.
    author_type = str(payload.get("author_type") or "person").strip()
    if author_type != "person":
        raise ValueError("invalid_author_type")
    return "POST", "https://api.linkedin.com/rest/posts", headers, {
        "author": f"urn:li:{author_type}:{account_id}",
        "commentary": text_value,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }


async def _claim_one() -> dict[str, Any] | None:
    async with SessionLocal() as session:
        async with session.begin():
            # A worker that disappeared while holding a processing action must not
            # cause an ambiguous provider POST to be replayed by another replica.
            await session.execute(text("""
                WITH stale AS (
                    UPDATE platform_actions
                    SET status='unknown',
                        error_code='executor_lease_expired',
                        error_message='Executor lease expired; provider outcome is unknown and was not replayed.',
                        completed_at=NOW(), updated_at=NOW()
                    WHERE status='processing'
                      AND updated_at < NOW() - INTERVAL '2 minutes'
                    RETURNING id
                )
                UPDATE social_post_drafts
                SET status='failed',
                    error_message='Provider outcome is unknown after executor interruption; automatic replay was suppressed.',
                    updated_at=NOW()
                WHERE platform_action_id IN (SELECT id FROM stale)
            """))
            row = (await session.execute(text("""
                WITH candidate AS (
                    SELECT id
                    FROM platform_actions
                    WHERE status = 'queued' AND updated_at <= NOW()
                    ORDER BY created_at, id
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE platform_actions AS a
                SET status = 'processing', updated_at = NOW()
                FROM candidate
                WHERE a.id = candidate.id
                RETURNING a.id, a.tenant_id, a.connection_id, a.platform, a.action,
                          a.target_type, a.target_id, a.request_payload, a.response_payload
            """))).mappings().one_or_none()
            return dict(row) if row else None


async def _finish(action_id: str, status: str, *, result: dict[str, Any] | None = None,
                  error_code: str | None = None, error_message: str | None = None) -> None:
    # Result payloads are provider IDs/status only; credentials and raw provider bodies
    # are never persisted or logged.
    async with SessionLocal() as session:
        await session.execute(text("""
            UPDATE platform_actions
            SET status=:status,
                response_payload=CAST(:result AS jsonb),
                error_code=:code,
                error_message=:message,
                completed_at=CASE WHEN :status IN ('succeeded','failed','unsupported','unknown') THEN NOW() ELSE NULL END,
                updated_at=NOW()
            WHERE id=:id
        """), {
            "id": action_id, "status": status,
            "result": json.dumps(result or {}),
            "code": error_code,
            "message": (error_message or "")[:240] or None,
        })
        draft_status = {
            "succeeded": "published",
            "failed": "failed",
            "unsupported": "failed",
            "unknown": "failed",
        }.get(status)
        if draft_status:
            await session.execute(text("""
                UPDATE social_post_drafts
                SET status=:draft_status, error_message=:message, updated_at=NOW()
                WHERE platform_action_id=:id
            """), {
                "id": action_id, "draft_status": draft_status,
                "message": (error_message or "")[:240] or None,
            })
        await session.commit()




async def _get_valid_access_token(
    *,
    token_id: str,
    tenant_id: str,
    user_id: str,
    connection_id: str,
    provider: str,
    encrypted_refresh: str | None,
    token_expires_at: datetime | None,
    scopes: list[str] | str,
) -> tuple[str, list[str]]:
    """Read or refresh a token under a DB row lock to prevent refresh-token races."""
    async with SessionLocal() as session:
        async with session.begin():
            connection = (await session.execute(text("""
                SELECT status, owner_user_id
                FROM social_connections
                WHERE tenant_id=:tenant AND id=:connection
                FOR UPDATE
            """), {"tenant": tenant_id, "connection": connection_id})).mappings().one_or_none()
            if (
                connection is None
                or connection["status"] != "connected"
                or connection["owner_user_id"] not in (None, user_id)
            ):
                raise ValueError("oauth_connection_unavailable")
            row = (await session.execute(text("""
                SELECT id, status, provider, encrypted_access_token,
                       encrypted_refresh_token, token_expires_at, refresh_token_expires_at, scopes
                FROM omnichannel_oauth_tokens
                WHERE id=:id AND tenant_id=:tenant AND user_id=:user
                FOR UPDATE
            """), {"id": token_id, "tenant": tenant_id, "user": user_id})).mappings().one_or_none()
            if row is None or row["status"] != "connected" or row["provider"] != provider:
                raise ValueError("oauth_grant_unavailable")
            current_scopes = row["scopes"] or []
            if isinstance(current_scopes, str):
                current_scopes = json.loads(current_scopes)
            expiry = row["token_expires_at"] or token_expires_at
            if expiry is not None and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            try:
                if not row["encrypted_access_token"]:
                    raise ValueError("oauth_access_token_missing")
                current_access = _fernet().decrypt(
                    str(row["encrypted_access_token"]).encode()
                ).decode()
            except (InvalidToken, RuntimeError, ValueError) as exc:
                raise ValueError("oauth_access_token_unreadable") from exc
            if expiry is None or expiry > datetime.now(UTC) + timedelta(minutes=5):
                return current_access, list(current_scopes)
            stored_refresh = row["encrypted_refresh_token"] or encrypted_refresh
            if not stored_refresh:
                raise ValueError("oauth_refresh_token_missing")
            refresh_expiry = row["refresh_token_expires_at"]
            if refresh_expiry is not None and refresh_expiry <= datetime.now(UTC):
                raise ValueError("oauth_refresh_token_expired")
            try:
                refresh_token = _fernet().decrypt(str(stored_refresh).encode()).decode()
            except (InvalidToken, RuntimeError, ValueError) as exc:
                raise ValueError("oauth_refresh_token_unreadable") from exc
            from app.api.omnichannel_oauth import refresh_provider_tokens
            refreshed = await refresh_provider_tokens(provider, refresh_token, list(current_scopes))
            new_access = str(refreshed["access_token"])
            new_refresh = str(refreshed["refresh_token"])
            new_scopes = list(refreshed["scopes"])
            new_expiry = refreshed["expires_at"]
            await session.execute(text("""
                UPDATE omnichannel_oauth_tokens
                SET encrypted_access_token=:access,
                    encrypted_refresh_token=:refresh,
                    token_expires_at=:expires,
                    refresh_token_expires_at=COALESCE(:refresh_expires, refresh_token_expires_at),
                    scopes=CAST(:scopes AS jsonb),
                    status='connected', updated_at=NOW()
                WHERE id=:id AND tenant_id=:tenant AND user_id=:user
            """), {
                "access": _fernet().encrypt(new_access.encode()).decode(),
                "refresh": _fernet().encrypt(new_refresh.encode()).decode(),
                "expires": new_expiry,
                "refresh_expires": refreshed.get("refresh_expires_at"),
                "scopes": json.dumps(new_scopes),
                "id": token_id, "tenant": tenant_id, "user": user_id,
            })
            await session.execute(text("""
                UPDATE social_connections
                SET token_expires_at=:expires, scopes=CAST(:scopes AS jsonb),
                    status='connected', updated_at=NOW()
                WHERE tenant_id=:tenant AND id=:connection
            """), {
                "expires": new_expiry, "scopes": json.dumps(new_scopes),
                "tenant": tenant_id, "connection": connection_id,
            })
            return new_access, new_scopes

async def process_action(action: dict[str, Any], *, client: httpx.AsyncClient | None = None) -> None:
    action_id = str(action["id"])
    platform = str(action["platform"])
    verb = str(action["action"])
    payload = action.get("request_payload") or {}
    if (platform, verb) not in SUPPORTED:
        await _finish(action_id, "unsupported", error_code="unsupported_action",
                      error_message="No approved provider adapter exists for this action.")
        return
    if not _approval_is_valid(action):
        await _finish(action_id, "failed", error_code="approval_required",
                      error_message="A human-approved action is required before provider execution.")
        return
    connection_id = action.get("connection_id")
    requested_by = str(payload.get("_requested_by") or "").strip()
    if not requested_by:
        await _finish(action_id, "failed", error_code="requester_missing",
                      error_message="The authenticated requesting user could not be verified.")
        return
    if not connection_id:
        await _finish(action_id, "failed", error_code="connection_required",
                      error_message="A connected provider account is required.")
        return

    async with SessionLocal() as session:
        row = (await session.execute(text("""
            SELECT c.status AS connection_status, c.platform_account_id,
                   t.id AS token_id, t.scopes AS scopes,
                   COALESCE(t.token_expires_at, c.token_expires_at) AS token_expires_at,
                   t.provider, t.encrypted_access_token, t.encrypted_refresh_token,
                   t.status AS token_status
            FROM social_connections c
            JOIN omnichannel_oauth_tokens t
              ON t.tenant_id=c.tenant_id
             AND t.platform=c.platform
             AND t.provider_account_id=c.platform_account_id
             AND t.user_id=:user
            WHERE c.tenant_id=:tenant AND c.id=:connection
              AND (c.owner_user_id=:user OR c.owner_user_id IS NULL)
        """), {"tenant": action["tenant_id"], "connection": connection_id, "user": requested_by})).mappings().one_or_none()
    if row is None:
        await _finish(action_id, "failed", error_code="connection_not_owned",
                      error_message="The selected provider account is missing or is not owned by the requesting user.")
        return
    if row["connection_status"] != "connected":
        await _finish(action_id, "failed", error_code="connection_unavailable",
                      error_message="The selected provider connection is not connected.")
        return
    if row["token_status"] != "connected" or not row["encrypted_access_token"]:
        await _finish(action_id, "failed", error_code="token_unavailable",
                      error_message="The encrypted provider token is unavailable; reconnect the account.")
        return
    if row["provider"] != TOKEN_PROVIDER[platform]:
        await _finish(action_id, "failed", error_code="provider_mismatch",
                      error_message="The stored OAuth provider does not match the requested platform.")
        return
    try:
        token, scopes = await _get_valid_access_token(
            token_id=str(row["token_id"]),
            tenant_id=str(action["tenant_id"]),
            user_id=requested_by,
            connection_id=str(connection_id),
            provider=str(row["provider"]),
            encrypted_refresh=str(row["encrypted_refresh_token"]) if row["encrypted_refresh_token"] else None,
            token_expires_at=row["token_expires_at"],
            scopes=row["scopes"] or [],
        )
    except Exception:
        log.exception("provider OAuth token preparation failed for action %s", action_id)
        await _finish(action_id, "failed", error_code="token_refresh_failed",
                      error_message="Provider token could not be prepared; reconnect the account and approve a new draft.")
        return
    required = REQUIRED_SCOPES[(platform, verb)]
    if required not in scopes:
        await _finish(action_id, "failed", error_code="scope_missing",
                      error_message="The connected account did not grant the required provider scope.")
        return

    # A disconnect cancels queued actions. Recheck the lease/state immediately
    # before the provider call so a just-cancelled action cannot start a new POST.
    async with SessionLocal() as session:
        still_processing = await session.scalar(text("""
            SELECT 1
            FROM platform_actions a
            JOIN social_connections c ON c.id=a.connection_id
            JOIN omnichannel_oauth_tokens t
              ON t.tenant_id=c.tenant_id AND t.platform=c.platform
             AND t.provider_account_id=c.platform_account_id
            WHERE a.id=:id AND a.status='processing'
              AND c.tenant_id=:tenant AND c.status='connected'
              AND (c.owner_user_id=:user OR c.owner_user_id IS NULL)
              AND t.user_id=:user AND t.status='connected'
        """), {"id": action_id, "tenant": action["tenant_id"], "user": requested_by})
    if not still_processing:
        return

    try:
        method, url, headers, request_body = _provider_request(
            platform, verb, token, str(row["platform_account_id"]), payload
        )
    except ValueError as exc:
        code = str(exc) if str(exc) in {"required_fields_missing", "invalid_author_type"} else "invalid_request"
        await _finish(action_id, "failed", error_code=code,
                      error_message="The action payload is invalid for this provider.")
        return

    own_client = client is None
    http = client or httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0))
    try:
        response = await http.request(method, url, headers=headers, json=request_body)
        disposition = _response_disposition(response.status_code)
        if disposition == "rate_limited":
            response_payload = payload.get("_executor") or {}
            attempt = int(response_payload.get("rate_limit_attempt", 0)) + 1
            if attempt < MAX_RATE_LIMIT_RETRIES:
                payload["_executor"] = {"rate_limit_attempt": attempt}
                delay_seconds = _rate_limit_delay_seconds(
                    response.headers.get("Retry-After"), attempt
                )
                async with SessionLocal() as session:
                    await session.execute(text("""
                        UPDATE platform_actions SET status='queued',
                          request_payload=CAST(:payload AS jsonb),
                          error_code='provider_rate_limited',
                          error_message='Provider rate limit; bounded retry scheduled.',
                          updated_at=NOW() + (:delay_seconds * INTERVAL '1 second')
                        WHERE id=:id AND status='processing'
                    """), {
                        "id": action_id, "payload": json.dumps(payload),
                        "delay_seconds": delay_seconds,
                    })
                    await session.commit()
                return
            await _finish(action_id, "failed", error_code="provider_rate_limited",
                          error_message="Provider rate limit persisted after bounded retries.")
            return
        if disposition in {"unauthorized", "forbidden"}:
            await _finish(action_id, "failed",
                          error_code="provider_unauthorized" if disposition == "unauthorized" else "provider_forbidden",
                          error_message="Provider rejected the connection or its granted permissions.")
            return
        if disposition == "unknown":
            # A 5xx may occur after a side effect. Never replay an ambiguous POST.
            await _finish(action_id, "unknown", error_code="provider_result_unknown",
                          error_message="Provider returned a server error; automatic replay was suppressed to avoid duplicates.")
            return
        if disposition == "rejected":
            await _finish(action_id, "failed", error_code="provider_rejected",
                          error_message=f"Provider rejected the request (HTTP {response.status_code}).")
            return
        try:
            data = response.json()
        except ValueError:
            data = {}
        nested_data = data.get("data") if isinstance(data, dict) else {}
        provider_id = (data.get("id") if isinstance(data, dict) else None) or (nested_data.get("id") if isinstance(nested_data, dict) else None) or response.headers.get("x-restli-id")
        await _finish(action_id, "succeeded", result={
            "provider": TOKEN_PROVIDER[platform],
            "provider_id": str(provider_id) if provider_id else None,
            "http_status": response.status_code,
        })
    except (httpx.TimeoutException, httpx.NetworkError):
        # A timeout does not prove the provider failed to perform the action.
        await _finish(action_id, "unknown", error_code="provider_result_unknown",
                      error_message="Provider request outcome is unknown; automatic replay was suppressed to avoid duplicates.")
    finally:
        if own_client:
            await http.aclose()


async def run_executor(stop_event: asyncio.Event) -> None:
    """Poll atomically claimed queue entries. Deployment must explicitly enable this."""
    while not stop_event.is_set():
        try:
            action = await _claim_one()
            if action:
                try:
                    await process_action(action)
                except Exception:
                    log.exception("omnichannel executor action failed unexpectedly")
                    try:
                        await _finish(str(action["id"]), "unknown", error_code="executor_internal_error",
                                      error_message="Executor encountered an internal error; automatic replay was suppressed.")
                    except Exception:
                        log.exception("could not persist terminal executor failure")
                continue
        except Exception:
            log.exception("omnichannel executor cycle failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=POLL_SECONDS)
        except TimeoutError:
            pass
