import json

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Event
from app.schemas.schemas import EventIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("/public", status_code=202)
async def track_public(body: EventIn, s: AsyncSession = Depends(db)):
    if body.name != "page_view":
        raise HTTPException(400, "Only page_view is accepted by the public collector")
    allowed = {
        "visitor_id", "page_path", "page_title", "landing_page", "referrer",
        "utm_source", "utm_medium", "utm_campaign", "language", "timezone",
        "device_category", "browser", "os", "screen_category", "logged_in",
    }
    properties = {}
    for key in allowed:
        value = body.properties.get(key)
        if value is not None:
            properties[key] = value if isinstance(value, bool) else str(value)[:512]
    if not properties.get("visitor_id"):
        raise HTTPException(400, "visitor_id is required")
    e = Event(
        tenant_id="default",
        user_id=None,
        name="page_view",
        properties=json.dumps(properties),
        source="web-public",
    )
    s.add(e)
    await s.commit()
    return {"accepted": True}


@router.post("", status_code=201)
async def track(body: EventIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    e = Event(
        tenant_id=user.get("tenant_id", "default"),
        user_id=user["sub"],
        name=body.name,
        properties=json.dumps(body.properties),
        source=body.source,
    )
    s.add(e)
    await s.commit()
    return {"id": e.id}


@router.get("/count")
async def count(
    name: str, days: int = 7, user=Depends(current_user), s: AsyncSession = Depends(db)
):
    from datetime import datetime, timedelta

    since = datetime.utcnow() - timedelta(days=days)
    res = await s.execute(
        select(func.count(Event.id)).where(
            Event.tenant_id == user.get("tenant_id", "default"),
            Event.name == name,
            Event.created_at >= since,
        )
    )
    return {"name": name, "days": days, "count": res.scalar()}


@router.get("/top")
async def top(
    days: int = 7, limit: int = 20, user=Depends(current_user), s: AsyncSession = Depends(db)
):
    from datetime import datetime, timedelta

    since = datetime.utcnow() - timedelta(days=days)
    res = await s.execute(
        select(Event.name, func.count(Event.id).label("c"))
        .where(Event.tenant_id == user.get("tenant_id", "default"), Event.created_at >= since)
        .group_by(Event.name)
        .order_by(desc("c"))
        .limit(limit)
    )
    return [{"name": n, "count": c} for n, c in res.all()]
