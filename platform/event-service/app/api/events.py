from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
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


@router.post("", status_code=201)
async def create(body: EventIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    e = Event(tenant_id=user.get("tenant_id", "default"), owner_id=user["sub"], **body.model_dump())
    s.add(e)
    await s.commit()
    await s.refresh(e)
    return {"id": e.id, "name": e.name}


@router.get("")
async def list_(s: AsyncSession = Depends(db)):
    res = await s.execute(select(Event).order_by(Event.starts_at.asc()))
    return [
        {
            "id": e.id,
            "name": e.name,
            "venue": e.venue,
            "starts_at": e.starts_at.isoformat(),
            "ends_at": e.ends_at.isoformat(),
            "capacity": e.capacity,
        }
        for e in res.scalars().all()
    ]


@router.get("/{event_id}")
async def get(event_id: str, s: AsyncSession = Depends(db)):
    e = (await s.execute(select(Event).where(Event.id == event_id))).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "not found")
    return {
        "id": e.id,
        "name": e.name,
        "venue": e.venue,
        "starts_at": e.starts_at.isoformat(),
        "ends_at": e.ends_at.isoformat(),
        "description": e.description,
        "is_online": e.is_online,
    }
