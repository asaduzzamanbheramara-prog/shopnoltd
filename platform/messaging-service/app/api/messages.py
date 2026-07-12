from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Message, Participant
from app.schemas.schemas import MsgIn, MsgOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/c/{conv_id}", response_model=MsgOut, status_code=201)
async def send(conv_id: str, body: MsgIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = (await s.execute(select(Participant).where(Participant.conversation_id == conv_id, Participant.user_id == user["sub"]))).scalar_one_or_none()
    if not p: raise HTTPException(403, "not a participant")
    m = Message(conversation_id=conv_id, sender_id=user["sub"], body=body.body, attachments=body.attachments)
    s.add(m); await s.commit(); await s.refresh(m)
    return MsgOut(id=m.id, conversation_id=m.conversation_id, sender_id=m.sender_id, body=m.body, created_at=m.created_at.isoformat())
@router.get("/c/{conv_id}", response_model=list[MsgOut])
async def list_msgs(conv_id: str, user=Depends(current_user), s: AsyncSession = Depends(db), limit: int = Query(50, le=200), offset: int = 0):
    p = (await s.execute(select(Participant).where(Participant.conversation_id == conv_id, Participant.user_id == user["sub"]))).scalar_one_or_none()
    if not p: raise HTTPException(403, "not a participant")
    res = await s.execute(select(Message).where(Message.conversation_id == conv_id, Message.deleted_at == None).order_by(Message.created_at.desc()).limit(limit).offset(offset))
    return [MsgOut(id=m.id, conversation_id=m.conversation_id, sender_id=m.sender_id, body=m.body, created_at=m.created_at.isoformat()) for m in res.scalars().all()]
@router.delete("/{msg_id}")
async def delete(msg_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    m = (await s.execute(select(Message).where(Message.id == msg_id))).scalar_one_or_none()
    if not m: raise HTTPException(404, "msg not found")
    if m.sender_id != user["sub"]: raise HTTPException(403, "not your message")
    from datetime import datetime
    m.deleted_at = datetime.utcnow()
    await s.commit()
    return {"ok": True}
