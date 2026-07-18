from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.mailcow import call_mailcow
from app.core.security import verify_token_admin
from app.models.models import Domain, Mailbox
from app.schemas.schemas import MailboxIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


@router.post("/{domain_id}", status_code=201)
async def add(domain_id: str, body: MailboxIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    d = (await s.execute(select(Domain).where(Domain.id == domain_id))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "domain not found")
    full = f"{body.local_part}@{d.name}"
    m = Mailbox(
        tenant_id=user.get("tenant_id", "default"),
        domain_id=d.id,
        local_part=body.local_part,
        full_address=full,
        quota_mb=body.quota_mb,
    )
    s.add(m)
    await s.commit()
    try:
        await call_mailcow(
            "add/mailbox",
            {
                "local_part": body.local_part,
                "domain": d.name,
                "password": "change-me-immediately",
                "password2": "change-me-immediately",
                "quota": body.quota_mb,
                "active": "1",
            },
        )
    except Exception:
        pass
    return {"id": m.id, "address": full}


@router.get("/{domain_id}")
async def list_mb(domain_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Mailbox).where(Mailbox.domain_id == domain_id))
    return [
        {"id": m.id, "address": m.full_address, "quota_mb": m.quota_mb, "active": m.active}
        for m in res.scalars().all()
    ]
