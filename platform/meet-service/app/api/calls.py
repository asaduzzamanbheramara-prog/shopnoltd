from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import CallSession, Participant, Room

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("/rooms/{room_name}")
async def start_call(room_name: str, call_type: str = "video", user=Depends(current_user), s: AsyncSession = Depends(db)):
    if call_type not in {"audio", "video"}:
        raise HTTPException(422, "call_type must be audio or video")
    room = (await s.execute(select(Room).where(Room.name == room_name))).scalar_one_or_none()
    if not room:
        raise HTTPException(404, "room not found")
    if room.owner_id != user["sub"]:
        participant = (await s.execute(select(Participant).where(
            Participant.room_id == room.id, Participant.user_id == user["sub"]
        ))).scalar_one_or_none()
        if not participant:
            raise HTTPException(403, "not a room participant")
    call = CallSession(tenant_id=user.get("tenant_id", "default"), room_id=room.id,
                       initiator_id=user["sub"], call_type=call_type, state="ringing")
    s.add(call)
    await s.commit()
    await s.refresh(call)
    return {"id": call.id, "room": room.name, "type": call.call_type, "state": call.state,
            "created_at": call.created_at.isoformat()}


@router.post("/{call_id}/accept")
async def accept_call(call_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    call = (await s.execute(select(CallSession).where(CallSession.id == call_id))).scalar_one_or_none()
    if not call:
        raise HTTPException(404, "call not found")
    participant = (await s.execute(select(Participant).where(
        Participant.room_id == call.room_id, Participant.user_id == user["sub"]
    ))).scalar_one_or_none()
    if user["sub"] != call.initiator_id and not participant:
        raise HTTPException(403, "not a call participant")
    call.state, call.answered_at = "active", datetime.utcnow()
    await s.commit()
    return {"id": call.id, "state": call.state, "answered_at": call.answered_at.isoformat()}


@router.post("/{call_id}/reject")
async def reject_call(call_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    call = (await s.execute(select(CallSession).where(CallSession.id == call_id))).scalar_one_or_none()
    if not call:
        raise HTTPException(404, "call not found")
    participant = (await s.execute(select(Participant).where(
        Participant.room_id == call.room_id, Participant.user_id == user["sub"]
    ))).scalar_one_or_none()
    if user["sub"] != call.initiator_id and not participant:
        raise HTTPException(403, "not a call participant")
    call.state, call.ended_at = "rejected", datetime.utcnow()
    await s.commit()
    return {"id": call.id, "state": call.state}


@router.post("/{call_id}/end")
async def end_call(call_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    call = (await s.execute(select(CallSession).where(CallSession.id == call_id))).scalar_one_or_none()
    if not call:
        raise HTTPException(404, "call not found")
    participant = (await s.execute(select(Participant).where(
        Participant.room_id == call.room_id, Participant.user_id == user["sub"]
    ))).scalar_one_or_none()
    if user["sub"] != call.initiator_id and not participant:
        raise HTTPException(403, "not a call participant")
    call.state, call.ended_at = "ended", datetime.utcnow()
    await s.commit()
    return {"id": call.id, "state": call.state, "ended_at": call.ended_at.isoformat()}


@router.get("/{call_id}")
async def call_status(call_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    call = (await s.execute(select(CallSession).where(CallSession.id == call_id))).scalar_one_or_none()
    if not call:
        raise HTTPException(404, "call not found")
    participant = (await s.execute(select(Participant).where(
        Participant.room_id == call.room_id, Participant.user_id == user["sub"]
    ))).scalar_one_or_none()
    if user["sub"] != call.initiator_id and not participant:
        raise HTTPException(403, "not a call participant")
    return {"id": call.id, "room_id": call.room_id, "type": call.call_type, "state": call.state,
            "created_at": call.created_at.isoformat(),
            "answered_at": call.answered_at.isoformat() if call.answered_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None}
