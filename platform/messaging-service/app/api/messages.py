import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Message, MessageReaction, Participant
from app.schemas.schemas import MsgIn, MsgOut
from shopno_core.database.redis import redis_client

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


def out(m: Message) -> MsgOut:
    return MsgOut(
        id=m.id, conversation_id=m.conversation_id, sender_id=m.sender_id,
        body=m.body, attachments=m.attachments or [], reply_to_id=m.reply_to_id,
        created_at=m.created_at.isoformat(), edited_at=m.edited_at.isoformat() if m.edited_at else None,
        deleted_at=m.deleted_at.isoformat() if m.deleted_at else None,
        status="deleted" if m.deleted_at else ("edited" if m.edited_at else "sent"),
    )


async def require_member(conv_id: str, user_id: str, s: AsyncSession):
    p = (await s.execute(select(Participant).where(
        Participant.conversation_id == conv_id, Participant.user_id == user_id
    ))).scalar_one_or_none()
    if not p:
        raise HTTPException(403, "not a participant")
    return p


async def publish_event(event: dict):
    await redis_client.publish(f"shopnoltd:messaging:{event['conversation_id']}", json.dumps(event))


@router.post("/c/{conv_id}", response_model=MsgOut, status_code=201)
async def send(conv_id: str, body: MsgIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    await require_member(conv_id, user["sub"], s)
    if not body.body.strip() and not body.attachments:
        raise HTTPException(422, "message body or attachment required")
    if body.reply_to_id:
        reply = (await s.execute(select(Message).where(
            Message.id == body.reply_to_id, Message.conversation_id == conv_id, Message.deleted_at == None
        ))).scalar_one_or_none()
        if not reply:
            raise HTTPException(400, "reply target not found")
    m = Message(conversation_id=conv_id, sender_id=user["sub"], body=body.body,
                attachments=body.attachments, reply_to_id=body.reply_to_id,
                client_message_id=body.client_message_id)
    s.add(m)
    await s.commit()
    await s.refresh(m)
    result = out(m)
    await publish_event({"type": "message", "conversation_id": conv_id, "message": result.model_dump()})
    return result


@router.get("/c/{conv_id}", response_model=list[MsgOut])
async def list_msgs(conv_id: str, user=Depends(current_user), s: AsyncSession = Depends(db),
                    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    await require_member(conv_id, user["sub"], s)
    res = await s.execute(select(Message).where(
        Message.conversation_id == conv_id, Message.deleted_at == None
    ).order_by(Message.created_at.desc()).limit(limit).offset(offset))
    return [out(m) for m in res.scalars().all()]


@router.patch("/{msg_id}", response_model=MsgOut)
async def edit(msg_id: str, body: MsgIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    m = (await s.execute(select(Message).where(Message.id == msg_id))).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "msg not found")
    await require_member(m.conversation_id, user["sub"], s)
    if m.sender_id != user["sub"]:
        raise HTTPException(403, "not your message")
    if m.deleted_at:
        raise HTTPException(409, "message deleted")
    if not body.body.strip() and not body.attachments:
        raise HTTPException(422, "message body or attachment required")
    m.body, m.attachments, m.edited_at = body.body, body.attachments, datetime.utcnow()
    await s.commit()
    await s.refresh(m)
    result = out(m)
    await publish_event({"type": "message.updated", "conversation_id": m.conversation_id, "message": result.model_dump()})
    return result


@router.post("/{msg_id}/reactions")
async def react(msg_id: str, reaction: str = Query(..., min_length=1, max_length=32),
                user=Depends(current_user), s: AsyncSession = Depends(db)):
    m = (await s.execute(select(Message).where(Message.id == msg_id, Message.deleted_at == None))).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "msg not found")
    await require_member(m.conversation_id, user["sub"], s)
    existing = (await s.execute(select(MessageReaction).where(
        MessageReaction.message_id == msg_id, MessageReaction.user_id == user["sub"], MessageReaction.reaction == reaction
    ))).scalar_one_or_none()
    if not existing:
        s.add(MessageReaction(message_id=msg_id, user_id=user["sub"], reaction=reaction))
        await s.commit()
        await publish_event({"type": "reaction", "conversation_id": m.conversation_id, "message_id": msg_id,
                             "user_id": user["sub"], "reaction": reaction})
    return {"reacted": True, "reaction": reaction}


@router.delete("/{msg_id}/reactions")
async def unreact(msg_id: str, reaction: str = Query(..., min_length=1, max_length=32),
                  user=Depends(current_user), s: AsyncSession = Depends(db)):
    m = (await s.execute(select(Message).where(Message.id == msg_id))).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "msg not found")
    await require_member(m.conversation_id, user["sub"], s)
    r = (await s.execute(select(MessageReaction).where(
        MessageReaction.message_id == msg_id, MessageReaction.user_id == user["sub"], MessageReaction.reaction == reaction
    ))).scalar_one_or_none()
    if r:
        await s.delete(r)
        await s.commit()
        await publish_event({"type": "reaction.removed", "conversation_id": m.conversation_id, "message_id": msg_id,
                             "user_id": user["sub"], "reaction": reaction})
    return {"unreacted": True, "reaction": reaction}


@router.get("/{msg_id}/reactions")
async def reactions(msg_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    m = (await s.execute(select(Message).where(Message.id == msg_id))).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "msg not found")
    await require_member(m.conversation_id, user["sub"], s)
    rows = (await s.execute(select(MessageReaction).where(MessageReaction.message_id == msg_id))).scalars().all()
    return [{"user_id": r.user_id, "reaction": r.reaction, "created_at": r.created_at.isoformat()} for r in rows]


@router.post("/c/{conv_id}/read")
async def mark_read(conv_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = await require_member(conv_id, user["sub"], s)
    p.last_read_at = datetime.utcnow()
    await s.commit()
    result = p.last_read_at.isoformat()
    await publish_event({"type": "read", "conversation_id": conv_id, "user_id": user["sub"], "read_at": result})
    return {"read_at": result}


@router.delete("/{msg_id}")
async def delete(msg_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    m = (await s.execute(select(Message).where(Message.id == msg_id))).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "msg not found")
    if m.sender_id != user["sub"]:
        raise HTTPException(403, "not your message")
    m.deleted_at = datetime.utcnow()
    await s.commit()
    await publish_event({"type": "message.deleted", "conversation_id": m.conversation_id, "message_id": m.id,
                         "user_id": user["sub"], "deleted_at": m.deleted_at.isoformat()})
    return {"ok": True, "deleted_at": m.deleted_at.isoformat()}
