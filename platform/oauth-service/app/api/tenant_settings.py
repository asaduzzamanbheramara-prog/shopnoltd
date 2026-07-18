from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import require_tenant_access
from app.models.models import Tenant
from app.schemas.schemas import TenantSettingsOut, TenantSettingsPatch

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


def _out(t: Tenant) -> TenantSettingsOut:
    s = t.settings or {}
    return TenantSettingsOut(
        tenant_id=t.id,
        theme=s.get("theme", {}),
        texts=s.get("texts", {}),
        plugins=s.get("plugins", {}),
    )


@router.get("/{tenant_id}/settings", response_model=TenantSettingsOut)
async def get(tenant_id: str, s: AsyncSession = Depends(db)):
    """Public read -- the storefront/portal needs this to render before login."""
    t = (await s.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "tenant not found")
    return _out(t)


@router.patch("/{tenant_id}/settings", response_model=TenantSettingsOut)
async def update(
    tenant_id: str,
    body: TenantSettingsPatch,
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    s: AsyncSession = Depends(db),
):
    """platform_admin or tenant_owner only. Only the keys present in the
    request body are merged in -- omit a key to leave it untouched, send an
    empty object ({}) to clear it."""
    await require_tenant_access(creds.credentials, tenant_id)
    t = (await s.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "tenant not found")
    current = dict(t.settings or {})
    if body.theme is not None:
        current["theme"] = {**current.get("theme", {}), **body.theme}
    if body.texts is not None:
        current["texts"] = {**current.get("texts", {}), **body.texts}
    if body.plugins is not None:
        current["plugins"] = {**current.get("plugins", {}), **body.plugins}
    t.settings = current
    await s.commit()
    await s.refresh(t)
    return _out(t)
