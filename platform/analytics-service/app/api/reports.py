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
