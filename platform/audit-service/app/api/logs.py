import hashlib, json
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import AuditLog
from app.schemas.schemas import LogIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", status_code=201)
async def log(body: LogIn, request: Request, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(AuditLog).where(AuditLog.tenant_id == user.get("tenant_id","default")).order_by(AuditLog.created_at.desc()).limit(1))
    prev = res.scalar_one_or_none()
    payload = {"tenant_id": user.get("tenant_id","default"), "actor_id": user["sub"], "action": body.action, "resource": body.resource, "data": body.data, "prev_hash": prev.hash if prev else ""}
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    e = AuditLog(tenant_id=payload["tenant_id"], actor_id=payload["actor_id"], action=body.action, resource=body.resource, resource_id=body.resource_id, ip=request.client.host if request.client else "", user_agent=request.headers.get("user-agent",""), data=json.dumps(body.data), prev_hash=payload["prev_hash"], hash=h)
    s.add(e); await s.commit()
    return {"id": e.id, "hash": h}
@router.get("")
async def list_(action: str = None, limit: int = Query(100, le=500), user=Depends(current_user), s: AsyncSession = Depends(db)):
    q = select(AuditLog).where(AuditLog.tenant_id == user.get("tenant_id","default"))
    if action: q = q.where(AuditLog.action == action)
    q = q.order_by(AuditLog.created_at.desc()).limit(limit)
    res = await s.execute(q)
    return [{"id": e.id, "actor_id": e.actor_id, "action": e.action, "resource": e.resource, "created_at": e.created_at.isoformat(), "hash": e.hash[:16]} for e in res.scalars().all()]
@router.get("/verify")
async def verify(limit: int = Query(1000, le=5000), user=Depends(current_user), s: AsyncSession = Depends(db)):
    """Walk the hash chain to prove no tampering."""
    res = await s.execute(select(AuditLog).where(AuditLog.tenant_id == user.get("tenant_id","default")).order_by(AuditLog.created_at.asc()).limit(limit))
    rows = res.scalars().all()
    valid = 0
    for e in rows:
        payload = {"tenant_id": e.tenant_id, "actor_id": e.actor_id, "action": e.action, "resource": e.resource, "data": json.loads(e.data or "{}"), "prev_hash": e.prev_hash}
        h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        if h == e.hash: valid += 1
    return {"checked": len(rows), "valid": valid, "tampered": len(rows) - valid}
