"""Fail-closed provider-backed executor for approved omnichannel actions.

Execution is opt-in. Only the adapters below can cause external side effects;
other platform/action combinations terminate as unsupported without a provider call.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text

from app.core.config import settings
from app.core.db import SessionLocal

log = logging.getLogger(__name__)

POLL_SECONDS = 3
MAX_RATE_LIMIT_RETRIES = 3
SUPPORTED = {
    ("gmail", "send_message"),
    ("outlook", "send_message"),
    ("x", "create_post"),
    ("linkedin", "create_post"),
}
SIDE_EFFECT_ACTIONS = {
    "send_message", "send_email", "create_post", "schedule_post", "comment",
    "reply", "like", "reaction", "share", "follow", "unfollow",
    "friend_request", "live", "call",
}
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


def _approval_is_valid(action: dict[str, Any]) -> bool:
    payload = action.get("request_payload") or {}
    approval = payload.get("approval") or {}
    return (
        approval.get("approved") is True
        and bool(str(approval.get("approved_by") or "").strip())
        and str(approval.get("approved_by") or "") == str(payload.get("_requested_by") or "")
        and not str(approval.get("approved_by") or "").startswith(("n8n-", "automation-"))
        and bool(str(approval.get("approved_at") or "").strip())
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
    author_type = str((payload.get("author_type") or "person")).strip()
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
            row = (await session.execute(text("""
                WITH candidate AS (
                    SELECT id
                    FROM platform_actions
                    WHERE status = 'queued'
                    ORDER BY created_at, id
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
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
        await session.commit()


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
            SELECT c.status AS connection_status, c.platform_account_id, c.scopes,
                   COALESCE(t.token_expires_at, c.token_expires_at) AS token_expires_at,
                   t.provider, t.encrypted_access_token, t.status AS token_status
            FROM social_connections c
            JOIN omnichannel_oauth_tokens t
              ON t.tenant_id=c.tenant_id
             AND t.platform=c.platform
             AND t.provider_account_id=c.platform_account_id
             AND t.user_id=:user
            WHERE c.tenant_id=:tenant AND c.id=:connection
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
    expiry = row["token_expires_at"]
    if expiry and expiry <= datetime.now(timezone.utc):
        await _finish(action_id, "failed", error_code="token_expired",
                      error_message="The provider token expired; reconnect the account before retrying.")
        return
    scopes = row["scopes"] or []
    if isinstance(scopes, str):
        try:
            scopes = json.loads(scopes)
        except ValueError:
            scopes = []
    required = REQUIRED_SCOPES[(platform, verb)]
    if required not in scopes:
        await _finish(action_id, "failed", error_code="scope_missing",
                      error_message="The connected account did not grant the required provider scope.")
        return
    try:
        token = _fernet().decrypt(str(row["encrypted_access_token"]).encode()).decode()
    except (InvalidToken, RuntimeError, ValueError):
        await _finish(action_id, "failed", error_code="token_decryption_failed",
                      error_message="The stored token could not be decrypted; reconnect the account.")
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
        if response.status_code == 429:
            response_payload = payload.get("_executor") or {}
            attempt = int(response_payload.get("rate_limit_attempt", 0)) + 1
            if attempt < MAX_RATE_LIMIT_RETRIES:
                payload["_executor"] = {"rate_limit_attempt": attempt}
                async with SessionLocal() as session:
                    await session.execute(text("""
                        UPDATE platform_actions SET status='queued',
                          request_payload=CAST(:payload AS jsonb),
                          error_code='provider_rate_limited',
                          error_message='Provider rate limit; bounded retry scheduled.',
                          updated_at=NOW() WHERE id=:id
                    """), {"id": action_id, "payload": json.dumps(payload)})
                    await session.commit()
                return
            await _finish(action_id, "failed", error_code="provider_rate_limited",
                          error_message="Provider rate limit persisted after bounded retries.")
            return
        if response.status_code in (401, 403):
            await _finish(action_id, "failed",
                          error_code="provider_unauthorized" if response.status_code == 401 else "provider_forbidden",
                          error_message="Provider rejected the connection or its granted permissions.")
            return
        if response.status_code >= 500:
            # A 5xx may occur after a side effect. Never replay an ambiguous POST.
            await _finish(action_id, "unknown", error_code="provider_result_unknown",
                          error_message="Provider returned a server error; automatic replay was suppressed to avoid duplicates.")
            return
        if response.status_code >= 400:
            await _finish(action_id, "failed", error_code="provider_rejected",
                          error_message=f"Provider rejected the request (HTTP {response.status_code}).")
            return
        try:
            data = response.json()
        except ValueError:
            data = {}
        provider_id = data.get("id") or data.get("message", {}).get("id") or response.headers.get("x-restli-id")
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
        except asyncio.TimeoutError:
            pass
