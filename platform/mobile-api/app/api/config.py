from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token, verify_token_admin
from app.models.models import AppConfig
from app.schemas.schemas import ConfigIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.get("/{code}")
async def get(code: str, s: AsyncSession = Depends(db)):
    cfg = (await s.execute(select(AppConfig).where(AppConfig.code == code))).scalar_one_or_none()
    if not cfg: return {"code": code, "data": {}}
    return {"code": cfg.code, "data": cfg.data, "updated_at": cfg.updated_at.isoformat()}
@router.post("", status_code=201)
async def set_(body: ConfigIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    cfg = (await s.execute(select(AppConfig).where(AppConfig.code == body.code))).scalar_one_or_none()
    if cfg: cfg.data = body.data
    else: s.add(AppConfig(code=body.code, data=body.data))
    await s.commit()
    return {"ok": True, "code": body.code}
