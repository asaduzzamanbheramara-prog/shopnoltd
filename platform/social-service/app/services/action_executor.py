from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import structlog
from sqlalchemy import text

from app.core.config import settings
from app.core.db import SessionLocal

log = structlog.get_logger()
POLL_SECONDS = 5
MAX_ATTEMPTS = 3


def telegram_message_payload(action: str, payload: dict[str, Any], target_id: str | None) -> dict[str, str]:
    if action != "send_message":
        raise ValueError("unsupported_action")
    chat_id = str(target_id or payload.get("chat_id") or "").strip()
    message = str(payload.get("text") or payload.get("message") or "").strip()
    if not chat_id:
        raise ValueError("target_chat_required")
    if not message:
        raise ValueError("message_text_required")
    if len(message) > 4096:
        raise ValueError("message_too_long")
    return {"chat_id": chat_id, "text": message}


async def _finish(s, action_id: str, status: str, *, result: dict | None = None,
                  code: str | None = None, message: str | None = None,
                  retry_after: int | None = None) -> None:
    await s.execute(text("""
        UPDATE platform_actions
        SET status=:status, response_payload=CAST(:result AS jsonb),
            error_code=:code, error_message=:message,
            next_attempt_at=CASE WHEN :delay IS NULL THEN NULL
              ELSE NOW() + (:delay * INTERVAL '1 second') END,
            completed_at=CASE WHEN :status IN ('succeeded','failed','unsupported','needs_review')
              THEN NOW() ELSE NULL END, updated_at=NOW()
        WHERE id=:id
    """), {"id": action_id, "status": status, "result": json.dumps(result or {}),
           "code": code, "message": message, "delay": retry_after})
    await s.commit()


async def process_one() -> bool:
    async with SessionLocal() as s:
        # Ambiguous interrupted requests require manual reconciliation; never replay automatically.
        await s.execute(text("""
            UPDATE platform_actions SET status='needs_review', error_code='worker_interrupted',
              error_message='Execution interrupted; reconcile provider state before retrying.',
              completed_at=NOW(), updated_at=NOW()
            WHERE status='processing' AND claimed_at < NOW() - INTERVAL '5 minutes'
        """))
        await s.commit()
        row = (await s.execute(text("""
            WITH candidate AS (
              SELECT id FROM platform_actions
              WHERE status IN ('queued','retry_wait')
                AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
                AND attempt_count < :max_attempts
              ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE platform_actions a SET status='processing',
              attempt_count=a.attempt_count+1, claimed_at=NOW(), updated_at=NOW()
            FROM candidate WHERE a.id=candidate.id
            RETURNING a.id,a.tenant_id,a.connection_id,a.platform,a.action,
              a.target_id,a.request_payload,a.attempt_count
        """), {"max_attempts": MAX_ATTEMPTS})).mappings().one_or_none()
        if row is None:
            return False
        action = dict(row)
        await s.commit()
        aid = str(action["id"])
        platform, verb = str(action["platform"]).lower(), str(action["action"]).lower()
        payload = action["request_payload"] or {}
        if isinstance(payload, str):
            payload = json.loads(payload)
        if platform != "telegram" or verb != "send_message":
            await _finish(s, aid, "unsupported", code="provider_action_not_implemented",
                          message="No verified provider adapter is available for this action.")
            return True
        conn = (await s.execute(text("""
            SELECT status,platform,platform_account_id,access_token_ref
            FROM social_connections
            WHERE id=:id AND tenant_id=:tenant
        """), {"id": action["connection_id"], "tenant": action["tenant_id"]})).mappings().one_or_none()
        if not conn or conn["platform"] != platform or conn["status"] != "connected":
            await _finish(s, aid, "failed", code="connection_not_ready",
                          message="The account connection is unavailable or not connected.")
            return True
        cap = (await s.execute(text("""
            SELECT availability FROM platform_capabilities WHERE platform=:platform AND action=:action
        """), {"platform": platform, "action": verb})).scalar_one_or_none()
        if cap != "supported":
            await _finish(s, aid, "unsupported", code="capability_not_verified",
                          message="Provider capability is not explicitly marked supported.")
            return True
        if not conn["access_token_ref"]:
            await _finish(s, aid, "failed", code="connection_credentials_not_bound",
                          message="This Telegram connection has no tenant-bound encrypted credential.")
            return True
        token_row = (await s.execute(text("""
            SELECT encrypted_access_token FROM omnichannel_oauth_tokens
            WHERE id::text=:ref AND tenant_id=:tenant AND provider='telegram'
              AND platform='telegram' AND provider_account_id=:account_id AND status='connected'
        """), {"ref": conn["access_token_ref"], "tenant": action["tenant_id"],
              "account_id": conn["platform_account_id"]})).mappings().one_or_none()
        if not token_row:
            await _finish(s, aid, "failed", code="connection_credentials_unavailable",
                          message="No matching tenant-bound Telegram credential is available.")
            return True
        try:
            from app.api.omnichannel_oauth import _fernet
            token = _fernet().decrypt(token_row["encrypted_access_token"].encode()).decode()
        except Exception:
            await _finish(s, aid, "failed", code="connection_credentials_unavailable",
                          message="The encrypted Telegram credential could not be resolved.")
            return True
        try:
            body = telegram_message_payload(verb, payload, action.get("target_id"))
        except ValueError as exc:
            await _finish(s, aid, "failed", code=str(exc),
                          message="Action payload is missing required fields or is invalid.")
            return True
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage", json=body)
        except (httpx.TimeoutException, httpx.NetworkError):
            await _finish(s, aid, "needs_review", code="provider_result_unknown",
                          message="Provider result is unknown; retry stopped to avoid duplicate delivery.")
            return True
        if response.status_code == 429 and int(action["attempt_count"]) < MAX_ATTEMPTS:
            try:
                delay = int(response.json().get("parameters", {}).get("retry_after", 5))
            except (ValueError, TypeError, json.JSONDecodeError):
                delay = 5
            await _finish(s, aid, "retry_wait", code="provider_rate_limited",
                          message="Provider rate limit; bounded retry scheduled.",
                          retry_after=min(max(delay, 1), 120))
            return True
        if response.status_code >= 500:
            await _finish(s, aid, "needs_review", code="provider_result_unknown",
                          message="Provider server error; retry stopped to avoid duplicate delivery.")
            return True
        if response.status_code >= 400:
            await _finish(s, aid, "failed", code="provider_rejected",
                          message=f"Provider rejected action (HTTP {response.status_code}).")
            return True
        try:
            result = response.json()
        except (ValueError, json.JSONDecodeError):
            result = {}
        if result.get("ok") is not True:
            await _finish(s, aid, "needs_review", code="provider_result_unverified",
                          message="Provider response did not confirm the action.")
            return True
        msg = result.get("result") or {}
        await _finish(s, aid, "succeeded", result={
            "provider": "telegram", "provider_message_id": msg.get("message_id"),
            "provider_chat_id": (msg.get("chat") or {}).get("id")})
        log.info("social_action.succeeded", action_id=aid, platform=platform, action=verb)
        return True


async def run_action_worker() -> None:
    log.info("social_action_worker.started", adapter_scope="telegram.send_message_only")
    while True:
        try:
            if not await process_one():
                await asyncio.sleep(POLL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Exception text may contain request details; log only a static event.
            log.error("social_action_worker.iteration_failed")
            await asyncio.sleep(POLL_SECONDS)
