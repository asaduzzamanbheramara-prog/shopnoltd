from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.powerdns import pdns_call
from app.core.security import verify_token_admin
from app.models.models import Registrar, Zone
from app.services.registrar_factory import get_adapter

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if creds is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await verify_token_admin(creds.credentials)


@router.get("")
async def list_registrars(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Registrar))
    return [{"id": r.id, "name": r.name, "enabled": r.enabled} for r in res.scalars().all()]


class DomainRegisterIn(BaseModel):
    domain: str
    years: int = 1
    contact: dict[str, Any]


@router.post("/{registrar_id}/register")
async def register_domain(
    registrar_id: str,
    body: DomainRegisterIn,
    user=Depends(admin),
    s: AsyncSession = Depends(db),
):
    registrar = (
        await s.execute(select(Registrar).where(Registrar.id == registrar_id))
    ).scalar_one_or_none()
    if not registrar:
        raise HTTPException(404, "registrar not found")
    if not registrar.enabled:
        raise HTTPException(400, f"registrar '{registrar.name}' is disabled")

    adapter = get_adapter(registrar)

    availability = await adapter.check_availability(body.domain)
    if not availability.get("available"):
        raise HTTPException(409, f"'{body.domain}' is not available")

    result = await adapter.register(body.domain, body.years, body.contact)

    z = Zone(tenant_id=user.get("tenant_id", "default"), name=body.domain, kind="MASTER")
    s.add(z)
    await s.commit()
    await s.refresh(z)
    try:
        await pdns_call(
            "POST",
            "/servers/localhost/zones",
            json={
                "name": body.domain + ".",
                "kind": "MASTER",
                "ttl": 3600,
                "nameservers": ["ns1.shopnoltd.dpdns.org.", "ns2.shopnoltd.dpdns.org."],
            },
        )
    except Exception:
        pass

    return {"zone_id": z.id, **result}
