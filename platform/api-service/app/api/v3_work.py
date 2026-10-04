"""Server-authoritative Work Evidence/Time Tracking API."""
import hashlib
import json
from datetime import datetime
from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.core.currencies import SUPPORTED_CURRENCIES
from app.models.work import Work, WorkAssignment, WorkSubmission
from app.models.work_evidence import WorkTaskConfig, WorkSession, WorkEvidence, WorkEvent, GlobalTaskRate

router = APIRouter(prefix="/work")
bearer = HTTPBearer()
PAYMENTS = "http://payment-service.shopno-payments.svc.cluster.local:80"


async def db():
    async with SessionLocal() as session:
        yield session


async def user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc


def tenant_ok(work, u):
    if not work:
        return False
    token_tenant = u.get("tenant_id") or u.get("tenant")
    return not token_tenant or work.tenant_id == token_tenant


def parse_json(value, default):
    try:
        return json.loads(value) if value else default
    except Exception:
        return default


def session_dict(x):
    return {
        "id": x.id,
        "work_id": x.work_id,
        "worker_id": x.worker_id,
        "stage": x.stage,
        "started_at": x.started_at.isoformat() if x.started_at else None,
        "ended_at": x.ended_at.isoformat() if x.ended_at else None,
        "work_seconds": x.work_seconds,
        "watch_seconds": x.watch_seconds,
        "interaction_seconds": x.interaction_seconds,
        "eligible_watch_seconds": x.eligible_watch_seconds,
        "calculated_amount": str(x.calculated_amount),
        "currency": x.currency,
    }


TASK_TYPES = {
    "simple", "job", "follow", "like", "comment", "share", "view", "visit",
    "review", "social", "data", "upload", "custom", "watch",
}

MICRO_TASK_TYPES = {"simple", "follow", "like", "comment", "share", "view", "visit", "review", "social", "data", "upload", "custom"}
WORK_PLATFORMS = {"shopnoltd", "facebook", "instagram", "youtube", "tiktok", "telegram", "whatsapp", "website", "data", "custom"}

def is_admin(u):
    roles = set(u.get("roles") or [])
    realm_roles = set(((u.get("realm_access") or {}).get("roles") or []))
    return bool(roles.intersection({"admin", "platform_admin", "shopnoltd-admin", "administrator"}) or realm_roles.intersection({"admin", "platform_admin", "shopnoltd-admin", "administrator"}) or u.get("is_admin") is True)

def rate_dict(r):
    return {"platform": r.platform, "task_type": r.task_type, "rate": str(r.rate), "currency": r.currency, "enabled": bool(r.enabled)}


def config_dict(c):
    return {
        "id": c.id,
        "work_id": c.work_id,
        "task_url": c.task_url,
        "media_url": c.media_url,
        "media_type": c.media_type,
        "required_watch_seconds": c.required_watch_seconds,
        "watch_rate_per_minute": str(c.watch_rate_per_minute),
        "rate_currency": c.rate_currency,
        "rate_rules": parse_json(c.rate_rules, []),
        "social_rates": parse_json(c.social_rates, {}),
    }


def calculate_amount(seconds, rate, rules):
    """Calculate each verified second against the configured stage it belongs to."""
    seconds = max(0, int(seconds))
    if seconds == 0:
        return Decimal("0.00000000")
    if not rules:
        return (Decimal(seconds) / Decimal(60) * rate).quantize(Decimal("0.00000001"))

    total = Decimal("0")
    ordered = sorted(rules, key=lambda r: int(r.get("from_second", 0)))
    for rule in ordered:
        start = max(0, int(rule.get("from_second", 0)))
        raw_end = rule.get("to_second")
        end = seconds if raw_end is None else max(start, int(raw_end))
        eligible = max(0, min(seconds, end) - start)
        if eligible:
            total += Decimal(eligible) / Decimal(60) * Decimal(str(rule.get("rate_per_minute", rate)))
    return total.quantize(Decimal("0.00000001"))


async def evidence_kinds(s, session_id, worker_id):
    result = await s.execute(
        select(WorkEvidence.kind).where(
            WorkEvidence.session_id == session_id,
            WorkEvidence.worker_id == worker_id,
            WorkEvidence.deleted_at.is_(None),
        )
    )
    return {row[0] for row in result.all()}


async def last_playback(s, session_id):
    result = await s.execute(
        select(WorkEvent)
        .where(WorkEvent.session_id == session_id, WorkEvent.event_type == "playback_heartbeat")
        .order_by(desc(WorkEvent.event_at))
        .limit(1)
    )
    return result.scalar_one_or_none()



@router.get("/rates")
async def get_task_rates(s: AsyncSession = Depends(db), u=Depends(user)):
    rows = (await s.execute(select(GlobalTaskRate).order_by(GlobalTaskRate.platform, GlobalTaskRate.task_type, GlobalTaskRate.currency))).scalars().all()
    rates = {}
    for r in rows:
        rates.setdefault(r.platform, {t: [] for t in sorted(TASK_TYPES)})
        rates[r.platform].setdefault(r.task_type, []).append(rate_dict(r))
    return {"supported_currencies": sorted(SUPPORTED_CURRENCIES), "platforms": sorted(WORK_PLATFORMS), "rates": rates}

@router.get("/balance-summary")
async def work_balance_summary(s: AsyncSession = Depends(db), u=Depends(user)):
    rows = (await s.execute(select(WorkSubmission).where(WorkSubmission.worker_id == u["sub"], WorkSubmission.status == "pending"))).scalars().all()
    due = {}
    for sub in rows:
        data = parse_json(sub.proof, {})
        cur = str(data.get("currency") or "USD").upper()
        due[cur] = due.get(cur, Decimal("0")) + Decimal(str(data.get("calculated_amount") or 0))
    return {"due_by_currency": {k: str(v.quantize(Decimal("0.00000001"))) for k,v in due.items()}, "pending_submission_count": len(rows)}

@router.get("/admin/rates")
async def admin_get_task_rates(s: AsyncSession = Depends(db), u=Depends(user)):
    if not is_admin(u):
        raise HTTPException(403, "admin role required")
    return await get_task_rates(s, u)

@router.put("/admin/rates/{task_type}/{currency}")
async def admin_set_task_rate(task_type: str, currency: str, body: dict, s: AsyncSession = Depends(db), u=Depends(user)):
    if not is_admin(u):
        raise HTTPException(403, "admin role required")
    platform = str(body.get("platform", "shopnoltd")).strip().lower()
    task_type = task_type.strip().lower()
    currency = currency.strip().upper()
    if platform not in WORK_PLATFORMS:
        raise HTTPException(422, f"Unsupported platform: {platform}")
    if task_type not in TASK_TYPES:
        raise HTTPException(422, f"Unsupported task_type: {task_type}")
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(422, f"Unsupported currency: {currency}")
    try:
        rate = Decimal(str(body.get("rate", 0)))
    except Exception as exc:
        raise HTTPException(422, "rate must be numeric") from exc
    if rate < 0:
        raise HTTPException(422, "rate cannot be negative")
    r = await s.scalar(select(GlobalTaskRate).where(
        GlobalTaskRate.platform == platform,
        GlobalTaskRate.task_type == task_type,
        GlobalTaskRate.currency == currency,
    ))
    if not r:
        r = GlobalTaskRate(platform=platform, task_type=task_type, currency=currency)
        s.add(r)
    r.rate = rate
    r.enabled = 1 if bool(body.get("enabled", True)) and rate > 0 else 0
    r.updated_at = datetime.utcnow()
    await s.commit()
    await s.refresh(r)
    return rate_dict(r)

@router.put("/admin/rates/{platform}/{task_type}/{currency}")
async def admin_set_platform_task_rate(platform: str, task_type: str, currency: str, body: dict, s: AsyncSession = Depends(db), u=Depends(user)):
    body = dict(body or {})
    body["platform"] = platform
    return await admin_set_task_rate(task_type, currency, body, s, u)

@router.delete("/admin/rates/{task_type}/{currency}")
async def admin_delete_task_rate(task_type: str, currency: str, s: AsyncSession = Depends(db), u=Depends(user)):
    if not is_admin(u):
        raise HTTPException(403, "admin role required")
    platform = str(task_type and "shopnoltd").strip().lower()
    currency = currency.strip().upper()
    if task_type.strip().lower() not in TASK_TYPES or currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(422, "unsupported task type or currency")
    r = await s.scalar(select(GlobalTaskRate).where(
        GlobalTaskRate.platform == platform,
        GlobalTaskRate.task_type == task_type.strip().lower(),
        GlobalTaskRate.currency == currency,
    ))
    if r:
        await s.delete(r)
        await s.commit()
    return {"deleted": True, "platform": platform, "task_type": task_type.strip().lower(), "currency": currency}

@router.delete("/admin/rates/{platform}/{task_type}/{currency}")
async def admin_delete_platform_task_rate(platform: str, task_type: str, currency: str, s: AsyncSession = Depends(db), u=Depends(user)):
    if not is_admin(u):
        raise HTTPException(403, "admin role required")
    platform = platform.strip().lower(); task_type = task_type.strip().lower(); currency = currency.strip().upper()
    if platform not in WORK_PLATFORMS or task_type not in TASK_TYPES or currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(422, "unsupported platform, task type or currency")
    r = await s.scalar(select(GlobalTaskRate).where(GlobalTaskRate.platform == platform, GlobalTaskRate.task_type == task_type, GlobalTaskRate.currency == currency))
    if r:
        await s.delete(r); await s.commit()
    return {"deleted": True, "platform": platform, "task_type": task_type, "currency": currency}

@router.get("/{work_id}/config")
async def get_config(work_id: str, s: AsyncSession = Depends(db), u=Depends(user)):
    w = await s.get(Work, work_id)
    if not tenant_ok(w, u):
        raise HTTPException(404, "work not found")
    c = await s.scalar(select(WorkTaskConfig).where(WorkTaskConfig.work_id == work_id))
    return config_dict(c) if c else {
        "work_id": work_id,
        "task_url": None,
        "media_url": None,
        "media_type": "none",
        "required_watch_seconds": 0,
        "watch_rate_per_minute": "0",
        "rate_currency": w.currency,
        "rate_rules": [],
        "social_rates": {},
    }


@router.put("/{work_id}/config")
async def put_config(work_id: str, body: dict, s: AsyncSession = Depends(db), u=Depends(user)):
    w = await s.get(Work, work_id)
    if not tenant_ok(w, u):
        raise HTTPException(404, "work not found")
    if w.creator_id != u["sub"]:
        raise HTTPException(403, "only the creator can configure work")
    if "task_type" in body:
        task_type = str(body["task_type"]).strip().lower()
        if task_type not in TASK_TYPES:
            raise HTTPException(422, f"Unsupported task_type: {task_type}")
        w.task_type = task_type
    c = await s.scalar(select(WorkTaskConfig).where(WorkTaskConfig.work_id == work_id))
    if not c:
        c = WorkTaskConfig(work_id=work_id)
        s.add(c)
    c.task_url = str(body.get("task_url") or "") or None
    c.media_url = str(body.get("media_url") or "") or None
    c.media_type = str(body.get("media_type") or "none").lower()
    c.required_watch_seconds = max(0, int(body.get("required_watch_seconds", 0)))
    c.watch_rate_per_minute = Decimal(str(body.get("watch_rate_per_minute", 0)))
    if c.watch_rate_per_minute < 0:
        raise HTTPException(422, "watch rate cannot be negative")
    c.rate_currency = str(body.get("rate_currency") or w.currency).upper()
    if c.rate_currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(422, "unsupported rate currency")
    c.rate_rules = json.dumps(body.get("rate_rules") or [])
    social_rates = body.get("social_rates") or {}
    if not isinstance(social_rates, dict):
        raise HTTPException(422, "social_rates must be an object")
    for key, value in social_rates.items():
        if str(key).lower() not in {"follow","like","comment","share","view","visit","review","social","custom"}:
            raise HTTPException(422, f"unsupported social rate type: {key}")
        try:
            if Decimal(str(value)) < 0: raise ValueError
        except Exception as exc:
            raise HTTPException(422, f"invalid social rate for {key}") from exc
    c.social_rates = json.dumps({str(k).lower(): str(v) for k,v in social_rates.items()})
    await s.commit()
    await s.refresh(c)
    return config_dict(c)


@router.post("/{work_id}/sessions", status_code=201)
async def create_session(work_id: str, s: AsyncSession = Depends(db), u=Depends(user)):
    w = await s.get(Work, work_id)
    if not tenant_ok(w, u):
        raise HTTPException(404, "work not found")
    a = await s.scalar(select(WorkAssignment).where(
        WorkAssignment.work_id == work_id,
        WorkAssignment.worker_id == u["sub"],
        WorkAssignment.status == "active",
    ))
    if not a:
        raise HTTPException(409, "accept the work before starting")
    active = await s.scalar(select(WorkSession).where(
        WorkSession.work_id == work_id,
        WorkSession.worker_id == u["sub"],
        WorkSession.stage.not_in(["finished", "submitted"]),
    ))
    if active:
        return session_dict(active)
    x = WorkSession(work_id=work_id, worker_id=u["sub"], stage="before", currency=w.currency)
    s.add(x)
    await s.commit()
    await s.refresh(x)
    return session_dict(x)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, s: AsyncSession = Depends(db), u=Depends(user)):
    x = await s.get(WorkSession, session_id)
    if not x or x.worker_id != u["sub"]:
        raise HTTPException(404, "session not found")
    return session_dict(x)


@router.post("/sessions/{session_id}/start")
async def start_session(session_id: str, s: AsyncSession = Depends(db), u=Depends(user)):
    x = await s.get(WorkSession, session_id)
    if not x or x.worker_id != u["sub"]:
        raise HTTPException(404, "session not found")
    if x.stage in {"finished", "submitted"}:
        raise HTTPException(409, "session already finished")
    kinds = await evidence_kinds(s, x.id, u["sub"])
    if "before" not in kinds:
        raise HTTPException(409, "required Before Work evidence must be captured before starting")
    if x.stage == "working":
        return session_dict(x)
    now = datetime.utcnow()
    x.stage = "working"
    x.started_at = x.started_at or now
    x.last_heartbeat_at = now
    s.add(WorkEvent(
        session_id=x.id,
        work_id=x.work_id,
        worker_id=u["sub"],
        event_type="work_started",
        event_at=now,
        rate_basis="server_start",
    ))
    await s.commit()
    return session_dict(x)


@router.post("/sessions/{session_id}/heartbeat")
async def heartbeat(session_id: str, body: dict, s: AsyncSession = Depends(db), u=Depends(user)):
    x = await s.get(WorkSession, session_id)
    if not x or x.worker_id != u["sub"]:
        raise HTTPException(404, "session not found")
    if x.stage != "working" or not x.last_heartbeat_at:
        raise HTTPException(409, "session is not working")

    now = datetime.utcnow()
    delta = min(max(int((now - x.last_heartbeat_at).total_seconds()), 0), 30)
    visible = bool(body.get("visible", False))
    playing = bool(body.get("playing", False))
    interaction = bool(body.get("interacting", False))
    position = body.get("position")
    ready = bool(body.get("ready", False))

    # Work time is always server elapsed time. Watch credit additionally requires
    # visibility, playback, readiness and plausible forward playback progress.
    x.work_seconds += delta
    previous = await last_playback(s, x.id)
    previous_payload = parse_json(previous.payload_json, {}) if previous else {}
    previous_position = previous_payload.get("position")
    try:
        current_position = float(position) if position is not None else None
        old_position = float(previous_position) if previous_position is not None else None
    except (TypeError, ValueError):
        current_position = old_position = None

    plausible_progress = (
        visible and playing and ready and delta > 0 and current_position is not None
        and (old_position is None or (-0.5 <= current_position - old_position <= delta + 2.0))
    )
    if plausible_progress:
        x.watch_seconds += delta
        x.eligible_watch_seconds += delta
    if visible and interaction:
        x.interaction_seconds += delta

    x.last_heartbeat_at = now
    payload = {
        "visible": visible,
        "playing": playing,
        "position": current_position,
        "ready": ready,
        "watch_credit": bool(plausible_progress),
        "verification": "server_elapsed_plus_playback_progress",
    }
    s.add(WorkEvent(
        session_id=x.id,
        work_id=x.work_id,
        worker_id=u["sub"],
        event_type="playback_heartbeat",
        event_at=now,
        duration_seconds=delta,
        payload_json=json.dumps(payload),
    ))
    c = await s.scalar(select(WorkTaskConfig).where(WorkTaskConfig.work_id == x.work_id))
    if c:
        x.calculated_amount = calculate_amount(
            x.eligible_watch_seconds,
            Decimal(str(c.watch_rate_per_minute)),
            parse_json(c.rate_rules, []),
        )
        x.currency = c.rate_currency
    await s.commit()
    return session_dict(x)


@router.post("/sessions/{session_id}/event")
async def event(session_id: str, body: dict, s: AsyncSession = Depends(db), u=Depends(user)):
    x = await s.get(WorkSession, session_id)
    if not x or x.worker_id != u["sub"]:
        raise HTTPException(404, "session not found")
    kind = str(body.get("event_type") or "").strip().lower()
    allowed = {"play", "pause", "seek", "buffer", "visibility_hidden", "visibility_visible", "like", "comment", "share", "follow", "rating", "link_open", "custom"}
    if kind not in allowed:
        raise HTTPException(422, "unsupported work event")
    c = await s.scalar(select(WorkTaskConfig).where(WorkTaskConfig.work_id == x.work_id))
    rates = parse_json(c.social_rates, {}) if c else {}
    basis = json.dumps({
        "rate": rates.get(kind),
        "currency": c.rate_currency if c else x.currency,
        "verification": "self_reported" if kind in {"like", "comment", "share", "follow", "rating"} else "telemetry_event",
        "reward_eligible": False if kind in {"like", "comment", "share", "follow", "rating"} else None,
    })
    now = datetime.utcnow()
    s.add(WorkEvent(
        session_id=x.id,
        work_id=x.work_id,
        worker_id=u["sub"],
        event_type=kind,
        event_at=now,
        rate_basis=basis,
        payload_json=json.dumps(body.get("payload") or {}),
    ))
    await s.commit()
    return {"recorded": True, "event_type": kind, "timestamp": now.isoformat(), "rate_basis": json.loads(basis)}


@router.post("/sessions/{session_id}/evidence", status_code=201)
async def evidence(session_id: str, body: dict, s: AsyncSession = Depends(db), u=Depends(user)):
    x = await s.get(WorkSession, session_id)
    if not x or x.worker_id != u["sub"]:
        raise HTTPException(404, "session not found")
    kind = str(body.get("kind") or "").lower()
    allowed = {"before", "start", "checkpoint", "complete", "end", "submit", "after_submission", "after_complete", "wrong", "failed", "social", "other"}
    if kind not in allowed:
        raise HTTPException(422, "unsupported evidence type")
    data = str(body.get("data_url") or "")
    url = str(body.get("evidence_url") or "")
    if not data and not url:
        raise HTTPException(422, "evidence data or URL is required")
    if len(data) > 8_000_000:
        raise HTTPException(413, "evidence image is too large")
    if kind == "before" and x.stage not in {"before", "working"}:
        raise HTTPException(409, "Before Work evidence can only be captured before or during work")
    if kind == "start" and x.stage not in {"before", "working"}:
        raise HTTPException(409, "Start Work evidence must be captured before or at work start")
    if kind in {"complete", "end"} and x.stage != "working":
        raise HTTPException(409, "Completion evidence requires an active work session")
    if kind in {"submit", "after_submission"} and x.stage not in {"finished", "submitted"}:
        raise HTTPException(409, "submission evidence requires completed work")
    if kind == "after_complete" and x.stage not in {"finished", "submitted"}:
        raise HTTPException(409, "after-complete evidence requires finished work")
    if kind == "end" and x.stage != "working":
        raise HTTPException(409, "End Work evidence requires an active work session")
    e = WorkEvidence(
        session_id=x.id,
        work_id=x.work_id,
        worker_id=u["sub"],
        kind=kind,
        title=str(body.get("title") or "") or None,
        evidence_url=url or None,
        data_url=data or None,
        metadata_json=json.dumps(body.get("metadata") or {}),
    )
    s.add(e)
    await s.flush()
    s.add(WorkEvent(
        session_id=x.id,
        work_id=x.work_id,
        worker_id=u["sub"],
        event_type="evidence_captured",
        event_at=e.captured_at,
        rate_basis="evidence_not_reward",
        payload_json=json.dumps({"evidence_id": e.id, "kind": kind}),
    ))
    await s.commit()
    await s.refresh(e)
    return {"id": e.id, "kind": e.kind, "title": e.title, "evidence_url": e.evidence_url, "captured_at": e.captured_at.isoformat()}


@router.get("/{work_id}/evidence")
async def list_evidence(work_id: str, s: AsyncSession = Depends(db), u=Depends(user)):
    w = await s.get(Work, work_id)
    if not tenant_ok(w, u):
        raise HTTPException(404, "work not found")
    result = await s.execute(
        select(WorkEvidence)
        .where(WorkEvidence.work_id == work_id, WorkEvidence.deleted_at.is_(None))
        .order_by(desc(WorkEvidence.captured_at))
    )
    return [
        {
            "id": e.id,
            "session_id": e.session_id,
            "kind": e.kind,
            "title": e.title,
            "evidence_url": e.evidence_url,
            "data_url": e.data_url,
            "metadata": parse_json(e.metadata_json, {}),
            "captured_at": e.captured_at.isoformat(),
        }
        for e in result.scalars().all()
        if e.worker_id == u["sub"] or w.creator_id == u["sub"]
    ]


@router.patch("/evidence/{evidence_id}")
async def edit_evidence(evidence_id: str, body: dict, s: AsyncSession = Depends(db), u=Depends(user)):
    e = await s.get(WorkEvidence, evidence_id)
    if not e or e.deleted_at:
        raise HTTPException(404, "evidence not found")
    w = await s.get(Work, e.work_id)
    if e.worker_id != u["sub"] and w.creator_id != u["sub"]:
        raise HTTPException(403, "not permitted")
    if "title" in body:
        e.title = str(body["title"]).strip() or None
    if "metadata" in body:
        e.metadata_json = json.dumps(body["metadata"] or {})
    now = datetime.utcnow()
    s.add(WorkEvent(
        session_id=e.session_id,
        work_id=e.work_id,
        worker_id=u["sub"],
        event_type="evidence_edited",
        event_at=now,
        payload_json=json.dumps({"evidence_id": e.id, "actor_id": u["sub"]}),
    ))
    await s.commit()
    return {"updated": True, "id": e.id}


@router.delete("/evidence/{evidence_id}")
async def delete_evidence(evidence_id: str, s: AsyncSession = Depends(db), u=Depends(user)):
    e = await s.get(WorkEvidence, evidence_id)
    if not e or e.deleted_at:
        raise HTTPException(404, "evidence not found")
    w = await s.get(Work, e.work_id)
    if e.worker_id != u["sub"] and w.creator_id != u["sub"]:
        raise HTTPException(403, "not permitted")
    e.deleted_at = datetime.utcnow()
    s.add(WorkEvent(
        session_id=e.session_id,
        work_id=e.work_id,
        worker_id=u["sub"],
        event_type="evidence_deleted",
        event_at=e.deleted_at,
        payload_json=json.dumps({"evidence_id": e.id, "actor_id": u["sub"]}),
    ))
    await s.commit()
    return {"deleted": True}


@router.post("/sessions/{session_id}/finish")
async def finish_session(session_id: str, s: AsyncSession = Depends(db), u=Depends(user)):
    x = await s.get(WorkSession, session_id)
    if not x or x.worker_id != u["sub"]:
        raise HTTPException(404, "session not found")
    if x.stage != "working":
        raise HTTPException(409, "session is not working")
    kinds = await evidence_kinds(s, x.id, u["sub"])
    w = await s.get(Work, x.work_id)
    if w and w.task_type == "watch":
        if "start" not in kinds:
            raise HTTPException(409, "required Start Work evidence must be captured")
        if "end" not in kinds:
            raise HTTPException(409, "required End Work evidence must be captured before finishing")
    elif not kinds and not await s.scalar(select(func.count(WorkEvent.id)).where(WorkEvent.session_id == x.id)):
        raise HTTPException(409, "complete the task and provide evidence or a task event before finishing")
    now = datetime.utcnow()
    if x.last_heartbeat_at:
        x.work_seconds += min(max(int((now - x.last_heartbeat_at).total_seconds()), 0), 30)
    x.ended_at = now
    x.stage = "finished"
    c = await s.scalar(select(WorkTaskConfig).where(WorkTaskConfig.work_id == x.work_id))
    if c:
        x.calculated_amount = calculate_amount(
            x.eligible_watch_seconds,
            Decimal(str(c.watch_rate_per_minute)),
            parse_json(c.rate_rules, []),
        )
        x.currency = c.rate_currency
    s.add(WorkEvent(
        session_id=x.id,
        work_id=x.work_id,
        worker_id=u["sub"],
        event_type="work_finished",
        event_at=now,
        rate_basis=json.dumps({
            "eligible_watch_seconds": x.eligible_watch_seconds,
            "amount": str(x.calculated_amount),
            "currency": x.currency,
            "verification": "server_calculated",
        }),
    ))
    await s.commit()
    return session_dict(x)


@router.post("/sessions/{session_id}/submit", status_code=201)
async def submit_session(session_id: str, s: AsyncSession = Depends(db), u=Depends(user)):
    x = await s.get(WorkSession, session_id)
    if not x or x.worker_id != u["sub"]:
        raise HTTPException(404, "session not found")
    if x.stage != "finished":
        raise HTTPException(409, "finish the work before submitting")
    c = await s.scalar(select(WorkTaskConfig).where(WorkTaskConfig.work_id == x.work_id))
    required_watch = int(c.required_watch_seconds) if c else 0
    kinds = await evidence_kinds(s, x.id, u["sub"])
    if x.eligible_watch_seconds < required_watch:
        raise HTTPException(409, f"required verified watch time not reached: {required_watch} seconds")
    if w := await s.get(Work, x.work_id):
        if w.task_type == "watch":
            if "before" not in kinds or "start" not in kinds or "end" not in kinds:
                raise HTTPException(409, "required Before, Start, and End evidence must be present")
        elif not kinds and not await s.scalar(select(func.count(WorkEvent.id)).where(WorkEvent.session_id == x.id)):
            raise HTTPException(409, "complete the task and provide evidence or a task event before submitting")
        if w.task_type in MICRO_TASK_TYPES:
            rate = Decimal(str(w.reward_amount))
            earning_currency = w.currency
            if c:
                configured = parse_json(c.social_rates, {})
                if w.task_type in configured:
                    rate = Decimal(str(configured[w.task_type]))
                    earning_currency = c.rate_currency
            if not c or w.task_type not in parse_json(c.social_rates, {}):
                global_rate = await s.scalar(select(GlobalTaskRate).where(
                    GlobalTaskRate.platform == w.platform,
                    GlobalTaskRate.task_type == w.task_type,
                    GlobalTaskRate.currency == w.currency,
                    GlobalTaskRate.enabled == 1,
                ))
                if global_rate:
                    rate = Decimal(str(global_rate.rate))
                    earning_currency = global_rate.currency
            x.calculated_amount = rate
            x.currency = earning_currency
    pending = await s.scalar(select(WorkSubmission).where(
        WorkSubmission.work_id == x.work_id,
        WorkSubmission.worker_id == u["sub"],
        WorkSubmission.status == "pending",
    ))
    if pending:
        raise HTTPException(409, "a submission is already pending")
    proof = json.dumps({
        "session_id": x.id,
        "work_seconds": x.work_seconds,
        "watch_seconds": x.watch_seconds,
        "eligible_watch_seconds": x.eligible_watch_seconds,
        "calculated_amount": str(x.calculated_amount),
        "currency": x.currency,
        "verification": "server_calculated",
    })
    sub = WorkSubmission(work_id=x.work_id, worker_id=u["sub"], proof=proof)
    s.add(sub)
    x.stage = "submitted"
    await s.commit()
    await s.refresh(sub)
    return {"id": sub.id, "session_id": x.id, "status": sub.status, "calculated_amount": str(x.calculated_amount), "currency": x.currency}


@router.post("/submissions/{submission_id}/approve")
async def approve_submission(submission_id: str, creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db), u=Depends(user)):
    sub = await s.get(WorkSubmission, submission_id)
    w = await s.get(Work, sub.work_id) if sub else None
    if not sub or not w:
        raise HTTPException(404, "submission not found")
    if w.creator_id != u["sub"]:
        raise HTTPException(403, "only the creator can approve")
    if sub.status != "pending":
        raise HTTPException(409, "submission already reviewed")
    data = parse_json(sub.proof, {})
    amount = Decimal(str(data.get("calculated_amount", 0)))
    currency = str(data.get("currency") or w.currency)
    if amount > 0:
        key = "work-evidence-settle:" + hashlib.sha256(sub.id.encode()).hexdigest()
        payload = {
            "to_user_id": sub.worker_id,
            "currency": currency,
            "amount": float(amount),
            "note": f"work:{sub.id}:verified-time",
            "idempotency_key": key,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{PAYMENTS}/api/v1/transfers",
                    headers={"Authorization": f"Bearer {creds.credentials}"},
                    json=payload,
                )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            raise HTTPException(503, "Payment service unavailable; submission remains pending") from exc
        if r.status_code >= 400:
            raise HTTPException(409, {"message": "verified reward settlement failed; submission remains pending", "payment_error": r.text})
        sub.review_note = f"Verified reward settled: {amount} {currency}"
    else:
        # No verified watch time / no configured rate produced a zero reward.
        # There is nothing to transfer, so calling payment-service would only
        # fail its amount>0 check and leave the submission stuck pending
        # forever. Approve it directly as a no-payout review instead.
        sub.review_note = "Approved with no verified reward (calculated amount was zero)"
    sub.status = "approved"
    sub.reviewer_id = u["sub"]
    sub.reviewed_at = datetime.utcnow()
    a = await s.scalar(select(WorkAssignment).where(WorkAssignment.work_id == w.id, WorkAssignment.worker_id == sub.worker_id))
    if a:
        a.status = "completed"
    await s.commit()
    return {"id": sub.id, "status": sub.status, "settled_amount": str(amount), "currency": currency}


@router.post("/submissions/{submission_id}/reject")
async def reject_submission(submission_id: str, body: dict = None, s: AsyncSession = Depends(db), u=Depends(user)):
    sub = await s.get(WorkSubmission, submission_id)
    w = await s.get(Work, sub.work_id) if sub else None
    if not sub or not w:
        raise HTTPException(404, "submission not found")
    if w.creator_id != u["sub"]:
        raise HTTPException(403, "only the creator can reject")
    if sub.status != "pending":
        raise HTTPException(409, "submission already reviewed")
    sub.status = "rejected"
    sub.reviewer_id = u["sub"]
    sub.reviewed_at = datetime.utcnow()
    sub.review_note = str((body or {}).get("note", "")) or "Rejected"
    # Release the worker's slot so it doesn't stay occupied forever by a
    # failed attempt, and reopen the task if a slot is now free again —
    # otherwise a rejected single-worker task could never be picked up by
    # anyone else, permanently stuck at "full" with no valid completer.
    a = await s.scalar(select(WorkAssignment).where(WorkAssignment.work_id == w.id, WorkAssignment.worker_id == sub.worker_id))
    if a:
        a.status = "rejected"
    if w.status == "full":
        active_count = await s.scalar(select(func.count(WorkAssignment.id)).where(WorkAssignment.work_id == w.id, WorkAssignment.status == "active"))
        if int(active_count or 0) < w.max_workers:
            w.status = "open"
    await s.commit()
    return {"id": sub.id, "status": sub.status, "work_status": w.status}
