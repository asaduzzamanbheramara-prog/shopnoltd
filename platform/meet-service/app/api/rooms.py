import jwt as pyjwt
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token
from app.models.models import Room, Participant
from app.schemas.schemas import RoomIn, RoomOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)

def make_jitsi_jwt(room: str, user_id: str, name: str, moderator: bool) -> str:
    return pyjwt.encode({
        "iss": settings.jitsi_jwt_app_id,
        "aud": settings.jitsi_jwt_app_id,
        "sub": settings.jitsi_url,
        "room": room,
        "exp": datetime.utcnow() + timedelta(hours=8),
        "nbf": datetime.utcnow(),
        "context": {"user": {"id": user_id, "name": name, "moderator": moderator}},
    }, settings.jitsi_jwt_secret, algorithm="HS256")

@router.post("", response_model=RoomOut, status_code=201)
async def create(body: RoomIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    r = Room(tenant_id=user.get("tenant_id","default"), name=body.name, owner_id=user["sub"], password_hash=secrets.hash(body.password) if body.password else None, is_recording=1 if body.recording else 0)
    s.add(r); await s.commit(); await s.refresh(r)
    s.add(Participant(room_id=r.id, user_id=user["sub"], role="moderator"))
    await s.commit()
    return RoomOut(id=r.id, name=r.name, owner_id=r.owner_id, is_recording=bool(r.is_recording), created_at=r.created_at.isoformat(), jitsi_url=f"{settings.jitsi_url}/{r.name}", jwt=make_jitsi_jwt(r.name, user["sub"], user.get("name", user["sub"]), True))
@router.get("/{name}/join", response_model=RoomOut)
async def join(name: str, password: Optional[str] = None, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Room).where(Room.name == name))
    r = res.scalar_one_or_none()
    if not r: raise HTTPException(404, "room not found")
    if r.password_hash and not secrets.compare_digest(secrets.hash(password) if password else "", r.password_hash):
        raise HTTPException(403, "wrong password")
    p = (await s.execute(select(Participant).where(Participant.room_id == r.id, Participant.user_id == user["sub"]))).scalar_one_or_none()
    if not p:
        s.add(Participant(room_id=r.id, user_id=user["sub"], role="member")); await s.commit()
    return RoomOut(id=r.id, name=r.name, owner_id=r.owner_id, is_recording=bool(r.is_recording), created_at=r.created_at.isoformat(), jitsi_url=f"{settings.jitsi_url}/{r.name}", jwt=make_jitsi_jwt(r.name, user["sub"], user.get("name", user["sub"]), False))
@router.get("", response_model=list[RoomOut])
async def list_rooms(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Room).where(Room.tenant_id == user.get("tenant_id","default")).order_by(Room.created_at.desc()).limit(100))
    return [RoomOut(id=r.id, name=r.name, owner_id=r.owner_id, is_recording=bool(r.is_recording), created_at=r.created_at.isoformat(), jitsi_url=f"{settings.jitsi_url}/{r.name}", jwt=make_jitsi_jwt(r.name, user["sub"], user.get("name", user["sub"]), False)) for r in res.scalars().all()]
@router.delete("/{name}")
async def end(name: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    r = (await s.execute(select(Room).where(Room.name == name))).scalar_one_or_none()
    if not r: raise HTTPException(404, "room not found")
    if r.owner_id != user["sub"]: raise HTTPException(403, "not owner")
    r.ended_at = datetime.utcnow()
    await s.commit()
    return {"ok": True}
