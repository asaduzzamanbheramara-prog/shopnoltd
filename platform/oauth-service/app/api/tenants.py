import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token_admin
from app.models.models import Tenant
from app.schemas.schemas import TenantIn, TenantOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.post("", response_model=TenantOut, status_code=201)
async def create(body: TenantIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    t = Tenant(name=body.name, subdomain=body.subdomain, plan=body.plan)
    s.add(t); await s.commit(); await s.refresh(t)
    return TenantOut(id=t.id, name=t.name, subdomain=t.subdomain, plan=t.plan)
@router.get("", response_model=list[TenantOut])
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Tenant))
    return [TenantOut(id=t.id, name=t.name, subdomain=t.subdomain, plan=t.plan) for t in res.scalars().all()]
@router.get("/{subdomain}", response_model=TenantOut)
async def by_subdomain(subdomain: str, s: AsyncSession = Depends(db)):
    t = (await s.execute(select(Tenant).where(Tenant.subdomain == subdomain))).scalar_one_or_none()
    if not t: raise HTTPException(404, "tenant not found")
    return TenantOut(id=t.id, name=t.name, subdomain=t.subdomain, plan=t.plan)
