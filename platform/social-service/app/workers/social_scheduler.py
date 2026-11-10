"""Approval-gated social schedule materializer.

This worker only turns due schedules into drafts. It never publishes or performs
external provider actions. Publishing requires a separate human approval action.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.db import SessionLocal
from sqlalchemy import text

log = logging.getLogger(__name__)
POLL_SECONDS = 15


def next_occurrence(
    now: datetime,
    local_time: time,
    timezone_name: str,
    days_of_week: list[int] | tuple[int, ...],
) -> datetime:
    """Return the next UTC occurrence; weekdays use Monday=0 through Sunday=6."""
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("unknown_timezone") from exc
    if not days_of_week or any(day not in range(7) for day in days_of_week):
        raise ValueError("invalid_days_of_week")
    if len(set(days_of_week)) != len(days_of_week):
        raise ValueError("duplicate_days_of_week")
    if local_time.tzinfo is not None or local_time.second or local_time.microsecond:
        raise ValueError("invalid_local_time")
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    now_utc = now.astimezone(UTC)
    local_now = now_utc.astimezone(zone)
    for offset in range(0, 9):
        candidate_date = local_now.date() + timedelta(days=offset)
        if candidate_date.weekday() not in days_of_week:
            continue
        candidate = datetime.combine(candidate_date, local_time.replace(tzinfo=None), tzinfo=zone)
        # Skip nonexistent wall-clock times during a DST spring-forward transition.
        for _ in range(181):
            round_trip = candidate.astimezone(UTC).astimezone(zone)
            if round_trip.replace(tzinfo=None) == candidate.replace(tzinfo=None):
                break
            candidate += timedelta(minutes=1)
        else:
            continue
        # Compare instants in UTC. Same-zone datetime comparisons can ignore
        # fold during the autumn DST transition and incorrectly return a past run.
        candidate_utc = candidate.astimezone(UTC)
        if candidate_utc > now_utc:
            return candidate_utc
    raise ValueError("no_next_occurrence")


async def materialize_one_due_schedule() -> bool:
    async with SessionLocal() as session:
        async with session.begin():
            row = (await session.execute(text("""
                SELECT s.id, s.tenant_id, s.user_id, s.connection_id, s.platform,
                       s.content_template, s.timezone, s.local_time, s.days_of_week,
                       s.next_run_at, c.status AS connection_status,
                       c.owner_user_id, t.status AS token_status, t.token_expires_at
                FROM social_automation_schedules s
                JOIN social_connections c
                  ON c.id=s.connection_id AND c.tenant_id=s.tenant_id
                LEFT JOIN omnichannel_oauth_tokens t
                  ON t.tenant_id=s.tenant_id AND t.platform=s.platform
                 AND t.provider_account_id=c.platform_account_id AND t.user_id=s.user_id
                WHERE s.enabled = TRUE AND s.next_run_at <= NOW()
                ORDER BY s.next_run_at, s.id
                LIMIT 1
                FOR UPDATE OF s SKIP LOCKED
            """))).mappings().one_or_none()
            if row is None:
                return False

            owner_mismatch = row["owner_user_id"] not in (None, row["user_id"])
            # Draft creation has no provider side effect. Keep generating drafts
            # after access-token expiry; publishing refreshes the grant or fails closed.
            account_unavailable = (
                row["connection_status"] != "connected"
                or row["token_status"] != "connected"
                or owner_mismatch
            )
            if account_unavailable:
                reason = (
                    "Connected account or OAuth grant is unavailable. Reconnect the account "
                    "and re-enable this schedule."
                )
                await session.execute(text("""
                    UPDATE social_automation_schedules
                    SET enabled=FALSE, paused_reason=:reason, updated_at=NOW()
                    WHERE id=:id
                """), {"id": row["id"], "reason": reason})
                return True

            occurrence = row["next_run_at"]
            local_time = row["local_time"]
            days = [int(day) for day in (row["days_of_week"] or [])]
            try:
                next_run = next_occurrence(
                    datetime.now(UTC),
                    local_time,
                    str(row["timezone"]),
                    days,
                )
            except ValueError:
                await session.execute(text("""
                    UPDATE social_automation_schedules
                    SET enabled=FALSE,
                        paused_reason='Invalid schedule timezone, local time, or weekday configuration.',
                        updated_at=NOW()
                    WHERE id=:id
                """), {"id": row["id"]})
                return True
            occurrence_key = occurrence.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
            content = str(row["content_template"]).strip()
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            await session.execute(text("""
                INSERT INTO social_post_drafts
                  (tenant_id, user_id, schedule_id, connection_id, platform, content,
                   status, scheduled_for, content_sha256, idempotency_key)
                VALUES
                  (:tenant, :user, :schedule, :connection, :platform, :content,
                   'pending_approval', :scheduled_for, :digest, :idem)
                ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
            """), {
                "tenant": row["tenant_id"],
                "user": row["user_id"],
                "schedule": row["id"],
                "connection": row["connection_id"],
                "platform": row["platform"],
                "content": content,
                "scheduled_for": occurrence,
                "digest": digest,
                "idem": f"schedule:{row['id']}:{occurrence_key}",
            })
            await session.execute(text("""
                UPDATE social_automation_schedules
                SET next_run_at=:next_run, last_run_at=:last_run,
                    paused_reason=NULL, updated_at=NOW()
                WHERE id=:id
            """), {"id": row["id"], "next_run": next_run, "last_run": occurrence})
            return True


async def run_scheduler(stop_event: asyncio.Event) -> None:
    """Create approval drafts for due schedules; no external API calls occur here."""
    while not stop_event.is_set():
        try:
            processed = await materialize_one_due_schedule()
            if processed:
                continue
        except Exception:
            log.exception("social schedule materialization failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=POLL_SECONDS)
        except TimeoutError:
            pass
