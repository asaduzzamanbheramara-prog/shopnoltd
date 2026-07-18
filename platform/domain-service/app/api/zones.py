from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.powerdns import pdns_call
from app.core.security import verify_token_admin
from app.models.models import Zone
from app.schemas.schemas import ZoneIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


@router.post("", status_code=201)
async def create_zone(body: ZoneIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    z = Zone(tenant_id=user.get("tenant_id", "default"), name=body.name, kind=body.kind)
    s.add(z)
    await s.commit()
    await s.refresh(z)
    try:
        await pdns_call(
            "POST",
            "/servers/localhost/zones",
            json={
                "name": body.name + ".",
                "kind": body.kind,
                "ttl": 3600,
                "nameservers": ["ns1.shopnoltd.dpdns.org.", "ns2.shopnoltd.dpdns.org."],
            },
        )
    except Exception:
        pass
    return {"id": z.id, "name": z.name}


@router.get("")
async def list_zones(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Zone))
    return [
        {"id": z.id, "name": z.name, "kind": z.kind, "active": z.active}
        for z in res.scalars().all()
    ]


@router.delete("/{zone_id}")
async def delete_zone(zone_id: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    z = (await s.execute(select(Zone).where(Zone.id == zone_id))).scalar_one_or_none()
    if not z:
        raise HTTPException(404, "not found")
    try:
        await pdns_call("DELETE", f"/servers/localhost/zones/{z.name}")
    except Exception:
        pass
    await s.delete(z)
    await s.commit()
    return {"ok": True}
