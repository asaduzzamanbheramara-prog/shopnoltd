from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Speaker, Event
from app.schemas.schemas import SpeakerIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/{event_id}", status_code=201)
async def add(event_id: str, body: SpeakerIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    e = (await s.execute(select(Event).where(Event.id == event_id))).scalar_one_or_none()
    if not e: raise HTTPException(404, "event not found")
    sp = Speaker(event_id=event_id, **body.model_dump())
    s.add(sp); await s.commit()
    return {"id": sp.id}
@router.get("/by-event/{event_id}")
async def list_speakers(event_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Speaker).where(Speaker.event_id == event_id))
    return [{"id": sp.id, "name": sp.name, "bio": sp.bio, "company": sp.company, "photo": sp.photo} for sp in res.scalars().all()]
