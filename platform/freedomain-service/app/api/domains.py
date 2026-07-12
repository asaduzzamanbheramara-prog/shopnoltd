import re
import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token
from app.models.models import FreeDomain
from app.schemas.schemas import RegisterIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
RESERVED = {"www","mail","api","admin","shopno","shopnoltd","ns1","ns2","mx","ftp","static","cdn"}
@router.post("", status_code=201)
async def register(body: RegisterIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    sub = body.subdomain.lower()
    if not NAME_RE.match(sub): raise HTTPException(400, "invalid subdomain")
    if sub in RESERVED: raise HTTPException(400, "subdomain reserved")
    full = f"{sub}.{settings.parent_zone}"
    if (await s.execute(select(FreeDomain).where(FreeDomain.subdomain == full))).scalar_one_or_none():
        raise HTTPException(409, "subdomain already taken")
    fd = FreeDomain(user_id=user["sub"], subdomain=full, target=body.target, record_type=body.record_type)
    s.add(fd); await s.commit()
    try:
        async with httpx.AsyncClient() as c:
            await c.post(f"{settings.domain_service_url}/api/v1/records", json={"zone_id": settings.parent_zone, "name": full, "type": body.record_type, "content": body.target, "ttl": 300}, headers={"Authorization": "Bearer admin-stub"})
    except Exception: pass
    return {"id": fd.id, "subdomain": full, "target": body.target}
@router.get("/me")
async def mine(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(FreeDomain).where(FreeDomain.user_id == user["sub"]))
    return [{"id": d.id, "subdomain": d.subdomain, "target": d.target, "record_type": d.record_type, "active": bool(d.active), "last_status": d.last_status, "created_at": d.created_at.isoformat()} for d in res.scalars().all()]
@router.get("/check-availability")
async def check(subdomain: str, s: AsyncSession = Depends(db)):
    sub = subdomain.lower()
    if not NAME_RE.match(sub) or sub in RESERVED:
        return {"available": False, "reason": "invalid or reserved"}
    full = f"{sub}.{settings.parent_zone}"
    exists = (await s.execute(select(FreeDomain).where(FreeDomain.subdomain == full))).scalar_one_or_none()
    return {"available": exists is None, "subdomain": full}
@router.delete("/{dom_id}")
async def delete(dom_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    fd = (await s.execute(select(FreeDomain).where(FreeDomain.id == dom_id, FreeDomain.user_id == user["sub"]))).scalar_one_or_none()
    if not fd: raise HTTPException(404, "not found")
    fd.active = 0
    await s.commit()
    return {"ok": True}
