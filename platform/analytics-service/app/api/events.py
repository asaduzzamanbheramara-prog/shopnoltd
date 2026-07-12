import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Event
from app.schemas.schemas import EventIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", status_code=201)
async def track(body: EventIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    e = Event(tenant_id=user.get("tenant_id","default"), user_id=user["sub"], name=body.name, properties=json.dumps(body.properties), source=body.source)
    s.add(e); await s.commit()
    return {"id": e.id}
@router.get("/count")
async def count(name: str, days: int = 7, user=Depends(current_user), s: AsyncSession = Depends(db)):
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)
    res = await s.execute(select(func.count(Event.id)).where(Event.tenant_id == user.get("tenant_id","default"), Event.name == name, Event.created_at >= since))
    return {"name": name, "days": days, "count": res.scalar()}
@router.get("/top")
async def top(days: int = 7, limit: int = 20, user=Depends(current_user), s: AsyncSession = Depends(db)):
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)
    res = await s.execute(
        select(Event.name, func.count(Event.id).label("c"))
        .where(Event.tenant_id == user.get("tenant_id","default"), Event.created_at >= since)
        .group_by(Event.name).order_by(desc("c")).limit(limit))
    return [{"name": n, "count": c} for n, c in res.all()]
