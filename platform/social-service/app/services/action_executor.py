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
    await s.commit()
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