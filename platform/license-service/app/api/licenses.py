import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token_admin
from app.models.models import License
from app.schemas.schemas import LicenseIn, LicenseOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.post("", response_model=LicenseOut, status_code=201)
async def create(body: LicenseIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    k = f"SHOPNO-{secrets.token_urlsafe(16).upper()}"
    lic = License(tenant_id=user.get("tenant_id","default"), key=k, plan=body.plan, features=body.features, seats=body.seats, expires_at=body.expires_at)
    s.add(lic); await s.commit()
    return LicenseOut(key=lic.key, plan=lic.plan, seats=lic.seats, expires_at=lic.expires_at, features=lic.features)
@router.post("/verify")
async def verify(key: str, s: AsyncSession = Depends(db)):
    lic = (await s.execute(select(License).where(License.key == key, License.revoked == 0))).scalar_one_or_none()
    if not lic: raise HTTPException(404, "invalid license")
    if lic.expires_at < datetime.utcnow(): raise HTTPException(403, "license expired")
    return {"valid": True, "plan": lic.plan, "seats": lic.seats, "features": lic.features, "expires_at": lic.expires_at.isoformat()}
@router.get("")
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(License).where(License.tenant_id == user.get("tenant_id","default")))
    return [{"key": l.key, "plan": l.plan, "seats": l.seats, "expires_at": l.expires_at.isoformat(), "revoked": bool(l.revoked)} for l in res.scalars().all()]
