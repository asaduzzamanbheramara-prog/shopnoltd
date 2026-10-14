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
    """Validate the one deliberately supported outbound action without side effects."""
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


async def _claim_one(s) -> dict[str, Any] | None:
    # Never automatically replay a request interrupted after it may have reached a provider.
    # Require reconciliation for stale processing rows instead of risking duplicate side effects.
    await s.execute(text(
        """
        UPDATE platform_actions
        SET status='needs_review', error_code='worker_interrupted',
            error_message='Worker stopped during execution; reconcile provider state before retrying.',
            completed_at=NOW(), updated_at=NOW()
        WHERE status='processing' AND claimed_at < NOW() - INTERVAL '5 minutes'
        """
    ))
    # Claim and increment in one statement. SKIP LOCKED permits safe scale-out.
    row = (await s.execute(text(
        """
        WITH candidate AS (
          SELECT id FROM platform_actions
          WHERE status IN ('queued', 'retry_wait')
            AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
            AND attempt_count < :max_attempts
          ORDER BY created_at
          FOR UPDATE SKIP LOCKED
          LIMIT 1
        )
        UPDATE platform_actions AS a
        SET status='processing', attempt_count=a.attempt_count + 1,
            claimed_at=NOW(), updated_at=NOW()
        FROM candidate
        WHERE a.id=candidate.id
        RETURNING a.id, a.tenant_id, a.connection_id, a.platform, a.action,
                  a.target_id, a.request_payload, a.attempt_count
        """
    ), {"max_attempts": MAX_ATTEMPTS})).mappings().one_or_none()
    if row is None:
        return None
    await s.commit()
    return dict(row)


async def _finish(s, action_id: str, status: str, *, result: dict[str, Any] | None = None,
                  error_code: str | None = None, error_message: str | None = None,
                  retry_after: int | None = None) -> None:
    # Persist only provider IDs and safe error codes/messages, never tokens or raw response bodies.
    await s.execute(text(
        """
        UPDATE platform_actions
        SET status=:status, response_payload=:result::jsonb,
            error_code=:error_code, error_message=:error_message,
            next_attempt_at=CASE WHEN :retry_after IS NULL THEN NULL
                                 ELSE NOW() + (:retry_after * INTERVAL '1 second') END,
            completed_at=CASE WHEN :status IN ('succeeded','failed','unsupported','needs_review')
                              THEN NOW() ELSE NULL END,
            updated_at=NOW()
        WHERE id=:id
        """
    ), {
        "id": action_id, "status": status,
        "result": json.dumps(result or {}),
        "error_code": error_code, "error_message": error_message,
        "retry_after": retry_after,
    })
    await s.commit()


async def process_one() -> bool:
    """Process at most one queued action. Unsupported providers/actions fail closed."""
    async with SessionLocal() as s:
        action = await _claim_one(s)
        if action is None:
            return False

        action_id = str(action["id"])
        platform = str(action["platform"]).lower()
        verb = str(action["action"]).lower()
        payload = action["request_payload"] or {}
        if isinstance(payload, str):
            payload = json.loads(payload)

        # This first adapter is intentionally narrow. Never claim generic provider-dependent
        # capabilities are executable until a provider-specific adapter and tests exist.
        if platform != "telegram" or verb != "send_message":
            await _finish(
                s, action_id, "unsupported",
                error_code="provider_action_not_implemented",
                error_message="No verified provider adapter is available for this action.",
            )
            return True

        if not settings.telegram_bot_token:
            await _finish(
                s, action_id, "failed", error_code="provider_not_configured",
                error_message="Telegram bot credentials are not configured.",
            )
            return True

        connection = (await s.execute(text(
            """
            SELECT id, status, platform, platform_account_id
            FROM social_connections
            WHERE id=:id AND tenant_id=:tenant
            """
        ), {"id": action["connection_id"], "tenant": action["tenant_id"]})).mappings().one_or_none()
        if connection is None:
            await _finish(s, action_id, "failed", error_code="connection_not_found",
                          error_message="The account connection is unavailable for this tenant.")
            return True
        if connection["platform"] != platform or connection["status"] != "connected":
            await _finish(s, action_id, "failed", error_code="connection_not_ready",
                          error_message="The account connection is not connected or does not match.")
            return True

        capability = (await s.execute(text(
            """SELECT availability FROM platform_capabilities
               WHERE platform=:platform AND action=:action"""
        ), {"platform": platform, "action": verb})).scalar_one_or_none()
        if capability != "supported":
            await _finish(s, action_id, "unsupported", error_code="capability_not_verified",
                          error_message="The provider capability is not explicitly marked supported.")
            return True

        try:
            body = telegram_message_payload(verb, payload, action.get("target_id"))
        except ValueError as exc:
            await _finish(s, action_id, "failed", error_code=str(exc),
                          error_message="The action payload is missing required fields or is invalid.")
            return True

        # Telegram 429 means the request was rejected and can be retried safely. Network
        # timeouts and 5xx are ambiguous: do not retry automatically and risk duplicate sends.
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json=body,
                )
        except (httpx.TimeoutException, httpx.NetworkError):
            await _finish(s, action_id, "needs_review", error_code="provider_result_unknown",
                          error_message="Provider result is unknown; automatic retry was stopped to avoid duplicate delivery.")
            return True

        if response.status_code == 429 and int(action["attempt_count"]) < MAX_ATTEMPTS:
            try:
                retry_after = int(response.json().get("parameters", {}).get("retry_after", 5))
            except (ValueError, TypeError, json.JSONDecodeError):
                retry_after = 5
            retry_after = min(max(retry_after, 1), 120)
            await _finish(s, action_id, "retry_wait", error_code="provider_rate_limited",
                          error_message="Provider rate limit; scheduled a bounded retry.",
                          retry_after=retry_after)
            return True

        if response.status_code >= 500:
            await _finish(s, action_id, "needs_review", error_code="provider_result_unknown",
                          error_message="Provider server error; automatic retry was stopped to avoid duplicate delivery.")
            return True
        if response.status_code >= 400:
            code = "provider_rate_limited" if response.status_code == 429 else "provider_rejected"
            await _finish(s, action_id, "failed", error_code=code,
                          error_message=f"Provider rejected the action (HTTP {response.status_code}).")
            return True

        try:
            result = response.json()
        except (ValueError, json.JSONDecodeError):
            await _finish(s, action_id, "needs_review", error_code="provider_result_invalid",
                          error_message="Provider response could not be verified.")
            return True
        if result.get("ok") is not True:
            await _finish(s, action_id, "failed", error_code="provider_rejected",
                          error_message="Provider did not confirm the action.")
            return True

        message = result.get("result") or {}
        await _finish(s, action_id, "succeeded", result={
            "provider": "telegram",
            "provider_message_id": message.get("message_id"),
            "provider_chat_id": (message.get("chat") or {}).get("id"),
        })
        log.info("social_action.succeeded", action_id=action_id, platform=platform, action=verb)
        return True


async def run_action_worker() -> None:
    """Long-running worker, disabled unless explicitly enabled in runtime config."""
    log.info("social_action_worker.started")
    while True:
        try:
            did_work = await process_one()
            if not did_work:
                await asyncio.sleep(POLL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Avoid logging exception text: database/provider errors can contain sensitive data.
            log.error("social_action_worker.iteration_failed")
            await asyncio.sleep(POLL_SECONDS)