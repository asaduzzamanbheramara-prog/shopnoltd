from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token_admin
from app.models.models import TenantRoute
from app.schemas.schemas import TenantRouteIn, TenantRouteOut

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


@router.post("", response_model=TenantRouteOut, status_code=201)
async def create(body: TenantRouteIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    if (
        await s.execute(select(TenantRoute).where(TenantRoute.subdomain == body.subdomain))
    ).scalar_one_or_none():
        raise HTTPException(409, "subdomain taken")
    ns = f"shopno-tenant-{body.subdomain}".replace(".", "-").replace("_", "-")
    r = TenantRoute(
        subdomain=body.subdomain,
        tenant_id=body.tenant_id,
        namespace=ns,
        plan=body.plan,
        storage_quota_gb=body.storage_quota_gb,
        user_quota=body.user_quota,
    )
    s.add(r)
    await s.commit()
    await s.refresh(r)
    return TenantRouteOut(
        subdomain=r.subdomain,
        tenant_id=r.tenant_id,
        namespace=r.namespace,
        plan=r.plan,
        storage_quota_gb=r.storage_quota_gb,
        user_quota=r.user_quota,
        active=r.active,
    )


@router.get("/by-host/{subdomain}", response_model=TenantRouteOut)
async def by_host(subdomain: str, s: AsyncSession = Depends(db)):
    full = (
        subdomain
        if subdomain.endswith(settings.base_domain)
        else f"{subdomain}.{settings.base_domain}"
    )
    r = (
        await s.execute(select(TenantRoute).where(TenantRoute.subdomain == full))
    ).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "tenant not found")
    return TenantRouteOut(
        subdomain=r.subdomain,
        tenant_id=r.tenant_id,
        namespace=r.namespace,
        plan=r.plan,
        storage_quota_gb=r.storage_quota_gb,
        user_quota=r.user_quota,
        active=r.active,
    )


@router.get("")
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(TenantRoute))
    return [
        TenantRouteOut(
            subdomain=r.subdomain,
            tenant_id=r.tenant_id,
            namespace=r.namespace,
            plan=r.plan,
            storage_quota_gb=r.storage_quota_gb,
            user_quota=r.user_quota,
            active=r.active,
        )
        for r in res.scalars().all()
    ]
