from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.powerdns import pdns_call
from app.core.security import verify_token_admin
from app.models.models import Record, Zone
from app.schemas.schemas import RecordIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


@router.post("", status_code=201)
async def create_record(body: RecordIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    z = (await s.execute(select(Zone).where(Zone.id == body.zone_id))).scalar_one_or_none()
    if not z:
        raise HTTPException(404, "zone not found")
    r = Record(
        zone_id=body.zone_id,
        name=body.name,
        type=body.type,
        content=body.content,
        ttl=body.ttl,
        priority=body.priority,
    )
    s.add(r)
    await s.commit()
    await s.refresh(r)
    try:
        await pdns_call(
            "PATCH",
            f"/servers/localhost/zones/{z.name}",
            json={
                "rrsets": [
                    {
                        "name": body.name + ".",
                        "type": body.type,
                        "ttl": body.ttl,
                        "changetype": "REPLACE",
                        "records": [{"content": body.content, "disabled": False}],
                    }
                ]
            },
        )
    except Exception:
        pass
    return {"id": r.id}


@router.get("/zone/{zone_id}")
async def list_records(zone_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Record).where(Record.zone_id == zone_id))
    return [
        {"id": r.id, "name": r.name, "type": r.type, "content": r.content, "ttl": r.ttl}
        for r in res.scalars().all()
    ]
