import qrcode, io, base64
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Ticket, Event
from app.schemas.schemas import TicketIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/{event_id}", status_code=201)
async def register(event_id: str, body: TicketIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    e = (await s.execute(select(Event).where(Event.id == event_id))).scalar_one_or_none()
    if not e: raise HTTPException(404, "event not found")
    qr = qrcode.QRCode(box_size=10, border=2); qr.add_data(f"shopno:{event_id}:{user['sub']}"); qr.make(fit=True)
    img = qr.make_image(); buf = io.BytesIO(); img.save(buf, format="PNG"); qr_b64 = base64.b64encode(buf.getvalue()).decode()
    t = Ticket(event_id=event_id, user_id=user["sub"], name=body.name, email=body.email, qr_code=qr_b64, price=0)
    s.add(t); await s.commit()
    return {"id": t.id, "qr": qr_b64}
@router.get("/me")
async def my(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Ticket).where(Ticket.user_id == user["sub"]))
    return [{"id": t.id, "event_id": t.event_id, "name": t.name, "status": t.status, "qr": t.qr_code} for t in res.scalars().all()]
