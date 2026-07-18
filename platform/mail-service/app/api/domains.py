from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.mailcow import call_mailcow
from app.core.security import verify_token_admin
from app.models.models import Domain
from app.schemas.schemas import DomainIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


@router.post("", status_code=201)
async def add(body: DomainIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    d = Domain(tenant_id=user.get("tenant_id", "default"), name=body.name)
    s.add(d)
    await s.commit()
    try:
        await call_mailcow("add/domain", {"domain": body.name, "active": "1"})
    except Exception:
        pass
    return {"id": d.id, "name": d.name}


@router.get("")
async def list_(s: AsyncSession = Depends(db)):
    res = await s.execute(select(Domain))
    return [{"id": d.id, "name": d.name, "active": d.active} for d in res.scalars().all()]
