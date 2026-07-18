from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Event
from app.models.models import Session as EventSession
from app.schemas.schemas import SessionIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("/{event_id}", status_code=201)
async def add(
    event_id: str, body: SessionIn, user=Depends(current_user), s: AsyncSession = Depends(db)
):
    e = (await s.execute(select(Event).where(Event.id == event_id))).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "event not found")
    ses = EventSession(event_id=event_id, **body.model_dump())
    s.add(ses)
    await s.commit()
    return {"id": ses.id}


@router.get("/by-event/{event_id}")
async def list_sessions(event_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(EventSession)
        .where(EventSession.event_id == event_id)
        .order_by(EventSession.starts_at.asc())
    )
    return [
        {
            "id": x.id,
            "title": x.title,
            "starts_at": x.starts_at.isoformat(),
            "ends_at": x.ends_at.isoformat(),
            "track": x.track,
            "room": x.room,
        }
        for x in res.scalars().all()
    ]
