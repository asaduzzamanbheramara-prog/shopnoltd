from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, time
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.omnichannel import current_user
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.social_capabilities import SOCIAL_POST_PLATFORMS
from app.workers.social_scheduler import next_occurrence

router = APIRouter()


async def _require_automation_schema() -> None:
    async with SessionLocal() as session:
        ready = bool(await session.scalar(text("""
            SELECT to_regclass('public.social_automation_schedules') IS NOT NULL
               AND to_regclass('public.social_post_drafts') IS NOT NULL
               AND to_regclass('public.omnichannel_oauth_tokens') IS NOT NULL
               AND to_regclass('public.platform_actions') IS NOT NULL
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='social_connections'
                     AND column_name='owner_user_id'
               )
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='social_automation_schedules'
                     AND column_name='paused_reason'
               )
               AND to_regclass('public.ux_social_automation_schedule_owner_slot') IS NOT NULL
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='omnichannel_oauth_tokens'
                     AND column_name='refresh_token_expires_at'
               )
        """)))
    if not ready:
        raise HTTPException(503, "social automation migration 021 is not fully installed")


def _identity(user: dict) -> tuple[str, str]:
    user_id = str(user.get("sub") or user.get("user_id") or "").strip()
    tenant_id = str(user.get("tenant_id") or "default").strip()
    if not user_id:
        raise HTTPException(401, "authenticated user identity is missing")
    return tenant_id, user_id


class ScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connection_id: UUID | None = None
    connection_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=25)
    content_template: str = Field(min_length=1, max_length=10000)
    timezone: str = Field(default="Asia/Dhaka", min_length=1, max_length=64)
    times: list[str] = Field(default_factory=lambda: ["09:00", "21:00"], min_length=2, max_length=2)
    days_of_week: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6], min_length=1, max_length=7)
    enabled: bool = False

    @model_validator(mode="after")
    def validate_connection_selection(self):
        if bool(self.connection_id) == bool(self.connection_ids):
            raise ValueError("provide either connection_id or connection_ids")
        if self.connection_ids and len(set(self.connection_ids)) != len(self.connection_ids):
            raise ValueError("connection_ids must be unique")
        return self

    @property
    def selected_connection_ids(self) -> list[UUID]:
        return self.connection_ids or [self.connection_id]


class DraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connection_id: UUID
    content: str = Field(min_length=1, max_length=10000)


class DraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=10000)


class ScheduleToggle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


async def _owned_connection(
    session: AsyncSession, tenant_id: str, user_id: str, connection_id: str
):
    row = (await session.execute(text("""
        SELECT c.id, c.platform, c.platform_account_id, c.status, c.scopes,
               c.owner_user_id, t.status AS token_status, t.token_expires_at,
               t.encrypted_refresh_token, t.refresh_token_expires_at,
               t.scopes AS token_scopes
        FROM social_connections c
        JOIN omnichannel_oauth_tokens t
          ON t.tenant_id=c.tenant_id AND t.platform=c.platform
         AND t.provider_account_id=c.platform_account_id AND t.user_id=:user
        WHERE c.tenant_id=:tenant AND c.id=:id
          AND (c.owner_user_id=:user OR c.owner_user_id IS NULL)
    """), {"tenant": tenant_id, "id": connection_id, "user": user_id})).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "connected OAuth account not found for this user")
    if row["platform"] not in SOCIAL_POST_PLATFORMS:
        raise HTTPException(409, "this connected account is not a supported social posting platform")
    if row["status"] != "connected" or row["token_status"] != "connected":
        raise HTTPException(409, "provider account is not connected; reconnect it first")
    expiry = row["token_expires_at"]
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    refresh_expiry = row["refresh_token_expires_at"]
    if (
        expiry is not None and expiry <= datetime.now(UTC)
        and (
            not row["encrypted_refresh_token"]
            or (refresh_expiry is not None and refresh_expiry <= datetime.now(UTC))
        )
    ):
        raise HTTPException(409, "provider access or refresh token expired; reconnect the account first")
    return row


@router.get("/status")
async def automation_status(user=Depends(current_user)):
    async with SessionLocal() as session:
        schema_ready = bool(await session.scalar(text("""
            SELECT to_regclass('public.social_automation_schedules') IS NOT NULL
               AND to_regclass('public.social_post_drafts') IS NOT NULL
               AND to_regclass('public.omnichannel_oauth_tokens') IS NOT NULL
               AND to_regclass('public.platform_actions') IS NOT NULL
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='social_connections'
                     AND column_name='owner_user_id'
               )
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='social_automation_schedules'
                     AND column_name='paused_reason'
               )
               AND to_regclass('public.ux_social_automation_schedule_owner_slot') IS NOT NULL
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='omnichannel_oauth_tokens'
                     AND column_name='refresh_token_expires_at'
               )
        """)))
    return {
        "scheduler_enabled": schema_ready,
        "executor_requested": bool(settings.omnichannel_executor_enabled),
        "executor_enabled": bool(
            schema_ready and settings.omnichannel_executor_enabled
            and settings.provider_oauth_encryption_ready
        ),
        "token_encryption_configured": bool(settings.provider_oauth_encryption_ready),
        "publishable_platforms": (
            ["x", "linkedin"]
            if schema_ready and settings.omnichannel_executor_enabled and settings.provider_oauth_encryption_ready
            else []
        ),
        "default_timezone": "Asia/Dhaka",
        "default_times": ["09:00", "21:00"],
        "approval_required": True,
    }


@router.post("/schedules", status_code=201)
async def create_schedules(body: ScheduleCreate, user=Depends(current_user)):
    await _require_automation_schema()
    tenant_id, user_id = _identity(user)
    content = body.content_template.strip()
    if not content:
        raise HTTPException(422, "content_template cannot be blank")
    if len(set(body.times)) != 2:
        raise HTTPException(422, "two different daily times are required")
    if any(day not in range(7) for day in body.days_of_week) or len(set(body.days_of_week)) != len(body.days_of_week):
        raise HTTPException(422, "days_of_week must contain unique values from 0 (Monday) to 6 (Sunday)")
    if any(not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value) for value in body.times):
        raise HTTPException(422, "times must use strict HH:MM local wall-clock format")
    try:
        ZoneInfo(body.timezone)
        parsed_times = [time.fromisoformat(value) for value in body.times]
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(422, "timezone or local time is invalid") from exc
    if any(value.tzinfo is not None or value.second or value.microsecond for value in parsed_times):
        raise HTTPException(422, "times must use HH:MM local wall-clock format")

    async with SessionLocal() as session:
        created = []
        for connection_id in body.selected_connection_ids:
            connection = await _owned_connection(session, tenant_id, user_id, connection_id)
            for local_time in parsed_times:
                schedule_id = str(uuid4())
                next_run = next_occurrence(
                    datetime.now(UTC), local_time, body.timezone, body.days_of_week
                )
                row = (await session.execute(text("""
                    INSERT INTO social_automation_schedules
                      (id, tenant_id, user_id, connection_id, platform, content_template,
                       timezone, local_time, days_of_week, next_run_at, enabled)
                    VALUES
                      (:id, :tenant, :user, :connection, :platform, :content,
                       :timezone, :local_time, :days, :next_run, :enabled)
                    ON CONFLICT (tenant_id, user_id, connection_id, local_time)
                    DO UPDATE SET content_template=EXCLUDED.content_template,
                                  timezone=EXCLUDED.timezone,
                                  days_of_week=EXCLUDED.days_of_week,
                                  next_run_at=EXCLUDED.next_run_at,
                                  enabled=EXCLUDED.enabled,
                                  paused_reason=CASE WHEN EXCLUDED.enabled
                                                     THEN NULL
                                                     ELSE social_automation_schedules.paused_reason END,
                                  updated_at=NOW()
                    RETURNING id, connection_id, platform, content_template, timezone,
                              local_time, days_of_week, next_run_at, enabled, created_at
                """), {
                    "id": schedule_id, "tenant": tenant_id, "user": user_id,
                    "connection": str(connection_id), "platform": connection["platform"],
                    "content": content, "timezone": body.timezone, "local_time": local_time,
                    "days": body.days_of_week, "next_run": next_run, "enabled": body.enabled,
                })).mappings().one()
                created.append(dict(row))
            # Replace stale time slots for each selected account. Existing drafts
            # remain intact because their schedule FK is ON DELETE SET NULL.
            await session.execute(text("""
                DELETE FROM social_automation_schedules
                WHERE tenant_id=:tenant AND user_id=:user AND connection_id=:connection
                  AND local_time NOT IN (:time_one, :time_two)
            """), {
                "tenant": tenant_id, "user": user_id,
                "connection": str(connection_id),
                "time_one": parsed_times[0], "time_two": parsed_times[1],
            })
        await session.commit()
    return {
        "schedules": created,
        "accounts_scheduled": len(body.selected_connection_ids),
        "note": "Each due occurrence creates a draft for your approval; nothing is published automatically.",
    }


@router.get("/schedules")
async def list_schedules(user=Depends(current_user)):
    await _require_automation_schema()
    tenant_id, user_id = _identity(user)
    async with SessionLocal() as session:
        rows = (await session.execute(text("""
            SELECT id, connection_id, platform, content_template, timezone, local_time,
                   days_of_week, next_run_at, enabled, paused_reason,
                   last_run_at, created_at, updated_at
            FROM social_automation_schedules
            WHERE tenant_id=:tenant AND user_id=:user
            ORDER BY local_time, platform
        """), {"tenant": tenant_id, "user": user_id})).mappings().all()
    return [dict(row) for row in rows]


@router.patch("/schedules/{schedule_id}")
async def set_schedule_enabled(schedule_id: UUID, body: ScheduleToggle, user=Depends(current_user)):
    await _require_automation_schema()
    tenant_id, user_id = _identity(user)
    async with SessionLocal() as session:
        schedule = (await session.execute(text("""
            SELECT connection_id FROM social_automation_schedules
            WHERE id=:id AND tenant_id=:tenant AND user_id=:user
        """), {"id": schedule_id, "tenant": tenant_id, "user": user_id})).mappings().one_or_none()
        if schedule is None:
            raise HTTPException(404, "schedule not found")
        if body.enabled:
            await _owned_connection(session, tenant_id, user_id, schedule["connection_id"])
        row = (await session.execute(text("""
            UPDATE social_automation_schedules
            SET enabled=:enabled,
                paused_reason=CASE WHEN :enabled THEN NULL ELSE 'Paused by user' END,
                updated_at=NOW()
            WHERE id=:id AND tenant_id=:tenant AND user_id=:user
            RETURNING id, enabled, next_run_at, paused_reason
        """), {
            "id": schedule_id, "tenant": tenant_id, "user": user_id,
            "enabled": body.enabled,
        })).mappings().one()
        await session.commit()
    return dict(row)


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: UUID, user=Depends(current_user)):
    await _require_automation_schema()
    tenant_id, user_id = _identity(user)
    async with SessionLocal() as session:
        result = await session.execute(text("""
            DELETE FROM social_automation_schedules
            WHERE id=:id AND tenant_id=:tenant AND user_id=:user
            RETURNING id
        """), {"id": schedule_id, "tenant": tenant_id, "user": user_id})
        if result.scalar_one_or_none() is None:
            raise HTTPException(404, "schedule not found")
        await session.commit()
    return None


@router.post("/drafts", status_code=201)
async def create_draft(body: DraftCreate, user=Depends(current_user)):
    await _require_automation_schema()
    tenant_id, user_id = _identity(user)
    content = body.content.strip()
    if not content:
        raise HTTPException(422, "content cannot be blank")
    async with SessionLocal() as session:
        connection = await _owned_connection(session, tenant_id, user_id, body.connection_id)
        draft_id = str(uuid4())
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        row = (await session.execute(text("""
            INSERT INTO social_post_drafts
              (id, tenant_id, user_id, connection_id, platform, content,
               status, content_sha256, idempotency_key)
            VALUES
              (:id, :tenant, :user, :connection, :platform, :content,
               'draft', :digest, :idem)
            RETURNING id, connection_id, platform, content, status,
                      content_sha256, created_at, updated_at
        """), {
            "id": draft_id, "tenant": tenant_id, "user": user_id,
            "connection": str(body.connection_id), "platform": connection["platform"],
            "content": content, "digest": digest, "idem": f"manual-draft:{draft_id}",
        })).mappings().one()
        await session.commit()
    return dict(row)


@router.get("/drafts")
async def list_drafts(user=Depends(current_user)):
    await _require_automation_schema()
    tenant_id, user_id = _identity(user)
    async with SessionLocal() as session:
        rows = (await session.execute(text("""
            SELECT d.id, d.schedule_id, d.connection_id, d.platform, d.content,
                   d.status, d.scheduled_for, d.content_sha256, d.approved_by,
                   d.approved_at, d.platform_action_id, d.error_message,
                   d.created_at, d.updated_at,
                   c.display_name, c.username, c.platform_account_id,
                   s.timezone AS schedule_timezone
            FROM social_post_drafts d
            JOIN social_connections c ON c.id=d.connection_id
            LEFT JOIN social_automation_schedules s ON s.id=d.schedule_id
            WHERE d.tenant_id=:tenant AND d.user_id=:user
            ORDER BY COALESCE(d.scheduled_for, d.created_at) DESC, d.created_at DESC
            LIMIT 200
        """), {"tenant": tenant_id, "user": user_id})).mappings().all()
    return [dict(row) for row in rows]


@router.patch("/drafts/{draft_id}")
async def update_draft(draft_id: UUID, body: DraftUpdate, user=Depends(current_user)):
    await _require_automation_schema()
    tenant_id, user_id = _identity(user)
    content = body.content.strip()
    if not content:
        raise HTTPException(422, "content cannot be blank")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    async with SessionLocal() as session:
        row = (await session.execute(text("""
            UPDATE social_post_drafts
            SET content=:content, content_sha256=:digest,
                status=CASE WHEN status='rejected' THEN 'draft' ELSE status END,
                error_message=NULL, updated_at=NOW()
            WHERE id=:id AND tenant_id=:tenant AND user_id=:user
              AND status IN ('draft','pending_approval','rejected')
            RETURNING id, platform, content, status, content_sha256, updated_at
        """), {
            "id": draft_id, "tenant": tenant_id, "user": user_id,
            "content": content, "digest": digest,
        })).mappings().one_or_none()
        if row is None:
            raise HTTPException(404, "editable draft not found")
        await session.commit()
    return dict(row)


@router.post("/drafts/{draft_id}/approve", status_code=202)
async def approve_draft(draft_id: UUID, user=Depends(current_user)):
    await _require_automation_schema()
    tenant_id, user_id = _identity(user)
    from app.workers.omnichannel_executor import REQUIRED_SCOPES, SUPPORTED, TOKEN_PROVIDER

    if not settings.omnichannel_executor_enabled:
        raise HTTPException(409, "provider publishing is disabled by the server; drafts and schedules remain available")
    if not settings.provider_oauth_encryption_ready:
        raise HTTPException(503, "provider token encryption is not configured")
    async with SessionLocal() as schema_session:
        schema_ready = bool((await schema_session.execute(
            text("SELECT to_regclass('public.social_post_drafts')")
        )).scalar())
    if not schema_ready:
        raise HTTPException(503, "social automation database migration is not installed")
    async with SessionLocal() as session:
        async with session.begin():
            draft = (await session.execute(text("""
                SELECT d.id, d.connection_id, d.platform, d.content, d.status,
                       d.content_sha256, c.platform_account_id, c.status AS connection_status,
                       c.owner_user_id, c.scopes AS connection_scopes,
                       t.provider, t.scopes AS token_scopes, t.status AS token_status,
                       t.token_expires_at, t.encrypted_refresh_token,
                       t.refresh_token_expires_at
                FROM social_post_drafts d
                JOIN social_connections c ON c.id=d.connection_id
                JOIN omnichannel_oauth_tokens t
                  ON t.tenant_id=c.tenant_id AND t.platform=c.platform
                 AND t.provider_account_id=c.platform_account_id AND t.user_id=d.user_id
                WHERE d.id=:id AND d.tenant_id=:tenant AND d.user_id=:user
                  AND (c.owner_user_id IS NULL OR c.owner_user_id=d.user_id)
                FOR UPDATE OF d
            """), {"id": draft_id, "tenant": tenant_id, "user": user_id})).mappings().one_or_none()
            if draft is None:
                raise HTTPException(404, "draft or owned OAuth connection not found")
            if draft["status"] not in {"draft", "pending_approval"}:
                raise HTTPException(409, "draft is not awaiting approval")
            platform = str(draft["platform"])
            if (platform, "create_post") not in SUPPORTED:
                raise HTTPException(409, f"{platform} publishing is not enabled: no tested provider adapter is installed")
            if draft["connection_status"] != "connected" or draft["token_status"] != "connected":
                raise HTTPException(409, "provider account is not connected")
            if draft["provider"] != TOKEN_PROVIDER.get(platform):
                raise HTTPException(409, "OAuth provider does not match the selected platform")
            expiry = draft["token_expires_at"]
            if expiry is not None and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            refresh_expiry = draft["refresh_token_expires_at"]
            if (
                expiry and expiry <= datetime.now(UTC)
                and (
                    not draft["encrypted_refresh_token"]
                    or (refresh_expiry is not None and refresh_expiry <= datetime.now(UTC))
                )
            ):
                raise HTTPException(409, "provider access or refresh token expired; reconnect the account")
            scopes = draft["token_scopes"] or []
            if isinstance(scopes, str):
                scopes = json.loads(scopes)
            required = REQUIRED_SCOPES[(platform, "create_post")]
            if required not in scopes:
                raise HTTPException(403, "provider account did not grant the required publishing scope")
            content = str(draft["content"]).strip()
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if digest != str(draft["content_sha256"]).strip():
                raise HTTPException(409, "draft content changed; refresh and review it again")
            approved_at = datetime.now(UTC).isoformat()
            action_id = str(uuid4())
            idem = f"social-draft:{draft_id}:{digest}"
            payload = {
                "text": content,
                "_requested_by": user_id,
                "approval": {
                    "approved": True,
                    "approved_by": user_id,
                    "approved_at": approved_at,
                    "content_sha256": digest,
                },
            }
            action = (await session.execute(text("""
                INSERT INTO platform_actions
                  (id, tenant_id, connection_id, platform, action, status,
                   idempotency_key, request_payload)
                VALUES
                  (:id, :tenant, :connection, :platform, 'create_post', 'queued',
                   :idem, CAST(:payload AS jsonb))
                ON CONFLICT (tenant_id, idempotency_key)
                DO UPDATE SET updated_at=NOW()
                RETURNING id, status
            """), {
                "id": action_id, "tenant": tenant_id, "connection": draft["connection_id"],
                "platform": platform, "idem": idem, "payload": json.dumps(payload),
            })).mappings().one()
            await session.execute(text("""
                UPDATE social_post_drafts
                SET status='queued', approved_by=:user, approved_at=:approved_at,
                    platform_action_id=:action, updated_at=NOW()
                WHERE id=:id
            """), {
                "id": draft_id, "user": user_id, "approved_at": approved_at,
                "action": action["id"],
            })
        return {"draft_id": draft_id, "action_id": str(action["id"]), "status": action["status"]}


@router.post("/drafts/{draft_id}/reject")
async def reject_draft(draft_id: UUID, user=Depends(current_user)):
    await _require_automation_schema()
    tenant_id, user_id = _identity(user)
    async with SessionLocal() as session:
        row = (await session.execute(text("""
            UPDATE social_post_drafts
            SET status='rejected', updated_at=NOW()
            WHERE id=:id AND tenant_id=:tenant AND user_id=:user
              AND status IN ('draft','pending_approval')
            RETURNING id, status
        """), {"id": draft_id, "tenant": tenant_id, "user": user_id})).mappings().one_or_none()
        if row is None:
            raise HTTPException(404, "rejectable draft not found")
        await session.commit()
    return dict(row)
