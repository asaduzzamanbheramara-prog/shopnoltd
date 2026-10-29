import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.mailcow import call_mailcow
from app.core.security import verify_token, verify_token_admin
from app.models.models import Domain, Mailbox
from app.schemas.schemas import MailboxIn, MailboxOwnerIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.get("/mine")
async def list_mine(user=Depends(current_user), s: AsyncSession = Depends(db)):
    user_id = str(user.get("sub", "")).strip()
    if not user_id:
        raise HTTPException(401, "invalid user identity")
    res = await s.execute(select(Mailbox).where(Mailbox.owner_user_id == user_id))
    return [
        {"id": m.id, "address": m.full_address, "quota_mb": m.quota_mb, "active": m.active}
        for m in res.scalars().all()
    ]


def _require_mailcow_success(response: object) -> None:
    # Mailcow's add/mailbox endpoint returns a list of result objects. HTTP 2xx
    # alone is insufficient: Mailcow can report application-level failures in JSON.
    if not isinstance(response, list) or not response:
        raise RuntimeError("Mailcow did not confirm mailbox creation")
    if any(not isinstance(item, dict) or item.get("type") != "success" for item in response):
        raise RuntimeError("Mailcow did not confirm mailbox creation")


@router.post("/{domain_id}", status_code=201)
async def add(domain_id: str, body: MailboxIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    d = (await s.execute(select(Domain).where(Domain.id == domain_id))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "domain not found")

    if body.quota_mb <= 0:
        raise HTTPException(422, "quota_mb must be positive")

    full = f"{body.local_part}@{d.name}"
    mailbox = Mailbox(
        tenant_id=user.get("tenant_id", "default"),
        owner_user_id=body.owner_user_id,
        domain_id=d.id,
        local_part=body.local_part,
        full_address=full,
        quota_mb=body.quota_mb,
        active=False,
    )
    s.add(mailbox)

    # Never use a shared/default password. This credential is deliberately not
    # returned or logged; a separate verified activation/reset flow is required
    # before this endpoint can be used for self-service signup.
    password = secrets.token_urlsafe(32)
    try:
        await s.flush()
        response = await call_mailcow(
            "add/mailbox",
            {
                "local_part": body.local_part,
                "domain": d.name,
                "password": password,
                "password2": password,
                "quota": body.quota_mb,
                "active": "1",
            },
        )
        _require_mailcow_success(response)
        mailbox.active = True
        await s.commit()
        await s.refresh(mailbox)
    except IntegrityError as exc:
        await s.rollback()
        raise HTTPException(409, "mailbox already exists") from exc
    except Exception as exc:
        await s.rollback()
        # Do not expose provider errors or credentials to the caller. A failed
        # provider request must never be reported as a successfully-created box.
        raise HTTPException(502, "mailbox provider provisioning failed") from exc

    return {"id": mailbox.id, "address": full, "active": mailbox.active}


@router.patch("/{mailbox_id}/owner")
async def assign_owner(
    mailbox_id: str,
    body: MailboxOwnerIn,
    user=Depends(admin),
    s: AsyncSession = Depends(db),
):
    owner_user_id = body.owner_user_id.strip()
    if not owner_user_id:
        raise HTTPException(422, "owner_user_id is required")
    mailbox = (
        await s.execute(select(Mailbox).where(Mailbox.id == mailbox_id))
    ).scalar_one_or_none()
    if not mailbox:
        raise HTTPException(404, "mailbox not found")
    mailbox.owner_user_id = owner_user_id
    await s.commit()
    await s.refresh(mailbox)
    return {"id": mailbox.id, "address": mailbox.full_address, "owner_user_id": mailbox.owner_user_id}


@router.get("/{domain_id}")
async def list_mb(
    domain_id: str,
    user=Depends(admin),
    s: AsyncSession = Depends(db),
):
    res = await s.execute(select(Mailbox).where(Mailbox.domain_id == domain_id))
    return [
        {"id": m.id, "address": m.full_address, "quota_mb": m.quota_mb, "active": m.active}
        for m in res.scalars().all()
    ]
