from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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


def _require_mailcow_success(response: object) -> None:
    # Mailcow may return HTTP 2xx while reporting an application-level failure.
    if not isinstance(response, list) or not response:
        raise RuntimeError("Mailcow did not confirm domain creation")
    if any(not isinstance(item, dict) or item.get("type") != "success" for item in response):
        raise RuntimeError("Mailcow did not confirm domain creation")


@router.post("", status_code=201)
async def add(body: DomainIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    d = Domain(tenant_id=user.get("tenant_id", "default"), name=body.name, active=False)
    s.add(d)
    try:
        # Flush first to detect local uniqueness conflicts before mutating Mailcow.
        await s.flush()
    except IntegrityError as exc:
        await s.rollback()
        raise HTTPException(409, "mail domain already exists") from exc

    try:
        response = await call_mailcow("add/domain", {"domain": body.name, "active": "1"})
        _require_mailcow_success(response)
        d.active = True
        await s.commit()
        await s.refresh(d)
    except Exception as exc:
        await s.rollback()
        # Do not return provider response bodies, URLs, or credentials to callers.
        raise HTTPException(502, "mail domain provider provisioning failed") from exc

    return {"id": d.id, "name": d.name, "active": bool(d.active)}


@router.get("")
async def list_(s: AsyncSession = Depends(db)):
    res = await s.execute(select(Domain))
    return [{"id": d.id, "name": d.name, "active": d.active} for d in res.scalars().all()]
