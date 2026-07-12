import asyncio
import aiosmtplib
from email.message import EmailMessage
import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.core.config import settings
from app.models.models import Notification, Template, NStatus, NChannel
from app.schemas.schemas import SendIn, Out
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jinja2 import Template as JinjaTemplate
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
async def send_email(to, subject, html):
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(html, subtype="html")
    await aiosmtplib.send(msg, hostname=settings.smtp_host, port=settings.smtp_port, username=settings.smtp_user, password=settings.smtp_password, start_tls=True)
async def send_sms(to, body):
    if not (settings.twilio_sid and settings.twilio_token): raise RuntimeError("twilio not configured")
    async with httpx.AsyncClient() as c:
        r = await c.post(f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_sid}/Messages.json",
            data={"To": to, "From": settings.smtp_from, "Body": body},
            auth=(settings.twilio_sid, settings.twilio_token))
        r.raise_for_status()
async def send_push(token, title, body):
    if not settings.fcm_server_key: raise RuntimeError("fcm not configured")
    async with httpx.AsyncClient() as c:
        r = await c.post("https://fcm.googleapis.com/fcm/send",
            json={"to": token, "notification": {"title": title, "body": body}},
            headers={"Authorization": f"key={settings.fcm_server_key}"})
        r.raise_for_status()

async def _send(n: Notification, subject: str, body: str):
    try:
        if n.channel == NChannel.email: await send_email(n.recipient, subject, body)
        elif n.channel == NChannel.sms: await send_sms(n.recipient, body)
        elif n.channel == NChannel.push: await send_push(n.recipient, subject, body)
        n.status = NStatus.sent
    except Exception as e:
        n.status = NStatus.failed; n.error = str(e)
    from datetime import datetime
    n.sent_at = datetime.utcnow()

@router.post("/send", response_model=Out, status_code=201)
async def send(body: SendIn, background: BackgroundTasks, user=Depends(current_user), s: AsyncSession = Depends(db)):
    subject = body.subject or "Shopnoltd"
    rendered = body.body
    if body.template_code:
        res = await s.execute(select(Template).where(Template.code == body.template_code))
        t = res.scalar_one_or_none()
        if not t: raise HTTPException(404, "template not found")
        subject = (t.subject or subject)
        rendered = JinjaTemplate(t.body).render(**body.variables)
    n = Notification(tenant_id=user.get("tenant_id","default"), user_id=user["sub"], channel=body.channel, status=NStatus.queued, subject=subject, body=rendered, recipient=body.recipient, meta=body.meta)
    s.add(n); await s.commit(); await s.refresh(n)
    background.add_task(_send, n, subject, rendered)
    await s.commit()
    return Out(id=n.id, channel=n.channel.value, status=n.status.value, recipient=n.recipient, created_at=n.created_at.isoformat(), sent_at=None)
@router.get("/me", response_model=list[Out])
async def my_notifications(user=Depends(current_user), s: AsyncSession = Depends(db), limit: int = 50):
    res = await s.execute(select(Notification).where(Notification.user_id == user["sub"]).order_by(Notification.created_at.desc()).limit(limit))
    return [Out(id=n.id, channel=n.channel.value, status=n.status.value, recipient=n.recipient, created_at=n.created_at.isoformat(), sent_at=n.sent_at.isoformat() if n.sent_at else None) for n in res.scalars().all()]
