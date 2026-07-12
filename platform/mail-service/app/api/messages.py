from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Message, Mailbox
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.get("/inbox/{mailbox_id}")
async def inbox(mailbox_id: str, user=Depends(current_user), s: AsyncSession = Depends(db), limit: int = Query(50, le=200), offset: int = 0):
    mb = (await s.execute(select(Mailbox).where(Mailbox.id == mailbox_id))).scalar_one_or_none()
    if not mb: raise HTTPException(404, "mailbox not found")
    res = await s.execute(select(Message).where(Message.mailbox_id == mailbox_id, Message.folder == "INBOX").order_by(desc(Message.received_at)).limit(limit).offset(offset))
    return [{"id": m.id, "from": m.from_addr, "subject": m.subject, "read": m.read, "received_at": m.received_at.isoformat()} for m in res.scalars().all()]
@router.get("/{msg_id}")
async def get(msg_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    m = (await s.execute(select(Message).where(Message.id == msg_id))).scalar_one_or_none()
    if not m: raise HTTPException(404, "not found")
    m.read = True; await s.commit()
    return {"id": m.id, "from": m.from_addr, "to": m.to_addrs, "subject": m.subject, "body": m.body, "received_at": m.received_at.isoformat()}
@router.post("/send")
async def send(from_mailbox_id: str, to: str, subject: str, body: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    mb = (await s.execute(select(Mailbox).where(Mailbox.id == from_mailbox_id))).scalar_one_or_none()
    if not mb: raise HTTPException(404, "from mailbox not found")
    from app.core.mailcow import call_mailcow
    try:
        await call_mailcow("add/message", {"from": mb.full_address, "to": to, "subject": subject, "plain": body})
    except Exception as e:
        raise HTTPException(500, f"send failed: {e}")
    return {"ok": True, "from": mb.full_address, "to": to}
