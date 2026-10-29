from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Mailbox, Message

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


def _is_platform_admin(user: dict) -> bool:
    # Only realm roles and this service's own client roles are authoritative;
    # an unrelated client's role named "admin" must not grant mailbox access.
    realm_access = user.get("realm_access") or {}
    roles = set(realm_access.get("roles") or [])
    resource_access = user.get("resource_access") or {}
    client_access = resource_access.get("mail-service") or {}
    roles.update(client_access.get("roles") or [])
    return bool(roles.intersection({"admin", "platform_admin"}))


def ensure_mailbox_access(mailbox: Mailbox, user: dict) -> None:
    """Fail closed: only the mailbox owner or a platform admin can access it."""
    if _is_platform_admin(user):
        return
    user_id = str(user.get("sub", "")).strip()
    if not user_id or mailbox.owner_user_id != user_id:
        # Use 404 so mailbox IDs cannot be enumerated across users.
        raise HTTPException(status_code=404, detail="mailbox not found")
    tenant_id = user.get("tenant_id")
    if tenant_id and mailbox.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="mailbox not found")


async def accessible_mailbox(mailbox_id: str, user: dict, s: AsyncSession) -> Mailbox:
    mailbox = (
        await s.execute(select(Mailbox).where(Mailbox.id == mailbox_id))
    ).scalar_one_or_none()
    if not mailbox:
        raise HTTPException(status_code=404, detail="mailbox not found")
    ensure_mailbox_access(mailbox, user)
    return mailbox


@router.get("/inbox/{mailbox_id}")
async def inbox(
    mailbox_id: str,
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    await accessible_mailbox(mailbox_id, user, s)
    res = await s.execute(
        select(Message)
        .where(Message.mailbox_id == mailbox_id, Message.folder == "INBOX")
        .order_by(desc(Message.received_at))
        .limit(limit)
        .offset(offset)
    )
    return [
        {
            "id": m.id,
            "from": m.from_addr,
            "subject": m.subject,
            "read": m.read,
            "received_at": m.received_at.isoformat(),
        }
        for m in res.scalars().all()
    ]


@router.get("/{msg_id}")
async def get(msg_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    message = (
        await s.execute(select(Message).where(Message.id == msg_id))
    ).scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="message not found")
    await accessible_mailbox(message.mailbox_id, user, s)
    message.read = True
    await s.commit()
    return {
        "id": message.id,
        "from": message.from_addr,
        "to": message.to_addrs,
        "subject": message.subject,
        "body": message.body,
        "received_at": message.received_at.isoformat(),
    }


@router.post("/send")
async def send(
    from_mailbox_id: str,
    to: str,
    subject: str,
    body: str,
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
):
    mailbox = await accessible_mailbox(from_mailbox_id, user, s)
    if not mailbox.active:
        raise HTTPException(status_code=409, detail="mailbox is inactive")
    from app.core.mailcow import call_mailcow

    try:
        await call_mailcow(
            "add/message",
            {"from": mailbox.full_address, "to": to, "subject": subject, "plain": body},
        )
    except Exception as exc:
        # Provider responses may contain internal addresses or configuration;
        # never forward them to an untrusted caller.
        raise HTTPException(status_code=502, detail="mail provider send failed") from exc
    return {"ok": True, "from": mailbox.full_address, "to": to}
