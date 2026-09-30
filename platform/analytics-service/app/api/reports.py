from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Event

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.get("/visitors")
async def visitors(days: int = 30, limit: int = 20, user=Depends(current_user), s: AsyncSession = Depends(db)):
    roles = set(user.get("roles", []))
    if not roles.intersection({"admin", "platform_admin", "tenant_owner"}):
        from fastapi import HTTPException
        raise HTTPException(403, "Analytics administration privileges required")
    days = max(1, min(days, 365))
    limit = max(1, min(limit, 100))
    since = datetime.utcnow() - timedelta(days=days)
    rows = (await s.execute(
        select(Event.properties).where(
            Event.tenant_id == "default",
            Event.name == "page_view",
            Event.created_at >= since,
        )
    )).scalars().all()
    events = []
    for raw in rows:
        try:
            value = __import__("json").loads(raw or "{}")
            if value.get("visitor_id"):
                events.append(value)
        except (TypeError, ValueError):
            continue

    def group(key):
        counts = {}
        for item in events:
            value = item.get(key) or "unknown"
            counts[value] = counts.get(value, 0) + 1
        return [{"value": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]]

    visitors_set = {item["visitor_id"] for item in events}
    returning = sum(
        1 for visitor in visitors_set
        if sum(1 for event in events if event["visitor_id"] == visitor) > 1
    )
    return {
        "days": days,
        "unique_visitors": len(visitors_set),
        "page_views": len(events),
        "sessions": len(visitors_set),
        "new_vs_returning": {"tracked_visitors": len(visitors_set), "returning_visitors": returning},
        "countries": [],
        "categories": {
            "device": group("device_category"),
            "browser": group("browser"),
            "os": group("os"),
            "language": group("language"),
            "referrer": group("referrer"),
            "landing_page": group("landing_page"),
            "page": group("page_path"),
            "campaign": group("utm_campaign"),
        },
    }


@router.get("/daily-active-users")
async def dau(days: int = 30, user=Depends(current_user), s: AsyncSession = Depends(db)):
    since = datetime.utcnow() - timedelta(days=days)
    res = await s.execute(
        select(
            func.date_trunc("day", Event.created_at).label("day"),
            func.count(func.distinct(Event.user_id)).label("u"),
        )
        .where(Event.tenant_id == user.get("tenant_id", "default"), Event.created_at >= since)
        .group_by("day")
        .order_by("day")
    )
    return [{"day": str(d), "users": u} for d, u in res.all()]


@router.get("/revenue")
async def revenue(days: int = 30, user=Depends(current_user), s: AsyncSession = Depends(db)):
    since = datetime.utcnow() - timedelta(days=days)
    res = await s.execute(
        select(
            func.date_trunc("day", Event.created_at).label("day"),
            func.sum(Event.properties.cast(__import__("sqlalchemy").Numeric)).label("r"),
        )
        .where(
            Event.tenant_id == user.get("tenant_id", "default"),
            Event.name == "payment.completed",
            Event.created_at >= since,
        )
        .group_by("day")
        .order_by("day")
    )
    return [{"day": str(d), "revenue": float(r or 0)} for d, r in res.all()]
