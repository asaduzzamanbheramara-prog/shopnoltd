from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token, verify_token_admin
from app.core.minio_client import client
from app.models.models import Bucket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.post("", status_code=201)
async def create(name: str, purpose: str = "general", user=Depends(admin), s: AsyncSession = Depends(db)):
    if not client.bucket_exists(name): client.make_bucket(name)
    b = Bucket(tenant_id=user.get("tenant_id","default"), name=name, purpose=purpose)
    s.add(b); await s.commit()
    return {"id": b.id, "name": b.name}
@router.get("")
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Bucket))
    return [{"name": b.name, "purpose": b.purpose} for b in res.scalars().all()]
