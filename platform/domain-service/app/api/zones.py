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
bearer = HTTPBearer(auto_error=False)


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if creds is None:
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return await verify_token_admin(creds.credentials)


def global_admin(user: dict) -> bool:
    return bool(set(user.get("roles", [])).intersection({"admin", "platform_admin"}))


@router.post("", status_code=201)
async def create_zone(body: ZoneIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    name = body.name.lower().rstrip(".")
    existing = (await s.execute(select(Zone).where(Zone.name == name))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "zone already exists")

    z = Zone(tenant_id=user.get("tenant_id", "default"), name=name, kind=body.kind)
    s.add(z)
    await s.flush()
    try:
        await pdns_call(
            "POST",
            "/servers/localhost/zones",
            json={
                "name": name + ".",
                "kind": body.kind,
                "ttl": 3600,
                "nameservers": ["ns1.shopnoltd.dpdns.org.", "ns2.shopnoltd.dpdns.org."],
            },
        )
    except Exception as exc:
        await s.rollback()
        raise HTTPException(502, f"PowerDNS zone creation failed: {exc}") from exc

    await s.commit()
    await s.refresh(z)
    return {"id": z.id, "name": z.name}


@router.get("")
async def list_zones(user=Depends(admin), s: AsyncSession = Depends(db)):
    query = select(Zone)
    if not global_admin(user):
        query = query.where(Zone.tenant_id == user.get("tenant_id", "default"))
    res = await s.execute(query)
    return [
        {"id": z.id, "name": z.name, "kind": z.kind, "active": z.active}
        for z in res.scalars().all()
    ]


@router.delete("/{zone_id}")
async def delete_zone(zone_id: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    query = select(Zone).where(Zone.id == zone_id)
    if not global_admin(user):
        query = query.where(Zone.tenant_id == user.get("tenant_id", "default"))
    z = (await s.execute(query)).scalar_one_or_none()
    if not z:
        raise HTTPException(404, "not found")
    try:
        await pdns_call("DELETE", f"/servers/localhost/zones/{z.name}")
    except Exception as exc:
        raise HTTPException(502, f"PowerDNS zone deletion failed: {exc}") from exc
    await s.delete(z)
    await s.commit()
    return {"ok": True}
