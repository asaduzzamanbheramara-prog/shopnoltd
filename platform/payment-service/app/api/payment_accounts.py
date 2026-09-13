"""Validated payment-account registry API.

Public responses intentionally exclude private account values and the editable
public_identifier field. Administrative responses are protected by the existing
payment-service admin authorization.
"""
import uuid
from datetime import datetime

from app.api.admin import require_admin
from app.core.db import SessionLocal
from app.models.models import AdminAuditLog, PaymentAccount
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


async def db():
    async with SessionLocal() as s:
        yield s


class PaymentAccountIn(BaseModel):
    provider: str = Field(min_length=2, max_length=32)
    account_label: str = Field(min_length=1, max_length=128)
    account_type: str = Field(default="manual", min_length=1, max_length=32)
    currency: str = Field(default="BDT", min_length=3, max_length=8)
    display_name: str | None = Field(default=None, max_length=128)
    masked_account: str | None = Field(default=None, max_length=128)
    public_identifier: str | None = Field(default=None, max_length=128)
    private_value: str | None = Field(default=None, max_length=256)
    instructions: str | None = Field(default=None, max_length=1000)
    qr_url: str | None = Field(default=None, max_length=2048)
    payment_url: str | None = Field(default=None, max_length=2048)
    status: str = Field(default="active", pattern=r"^(active|inactive)$")
    sort_order: int = Field(default=0, ge=0, le=100000)
    tenant_id: str | None = Field(default=None, max_length=64)


class PaymentAccountPatch(BaseModel):
    provider: str | None = Field(default=None, min_length=2, max_length=32)
    account_label: str | None = Field(default=None, min_length=1, max_length=128)
    account_type: str | None = Field(default=None, min_length=1, max_length=32)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    display_name: str | None = Field(default=None, max_length=128)
    masked_account: str | None = Field(default=None, max_length=128)
    public_identifier: str | None = Field(default=None, max_length=128)
    private_value: str | None = Field(default=None, max_length=256)
    instructions: str | None = Field(default=None, max_length=1000)
    qr_url: str | None = Field(default=None, max_length=2048)
    payment_url: str | None = Field(default=None, max_length=2048)
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")
    sort_order: int | None = Field(default=None, ge=0, le=100000)


def _tenant(user, requested=None):
    roles = set(user.get("roles", []))
    current = user.get("tenant_id") or "default"
    if requested and requested != current and "platform_admin" not in roles:
        raise HTTPException(403, "platform_admin required to manage another tenant")
    return requested or current


def _public(row):
    return {
        "id": str(row.id),
        "provider": row.provider,
        "account_label": row.account_label,
        "account_type": row.account_type,
        "currency": row.currency,
        "display_name": row.display_name,
        "masked_account": row.masked_account,
        "instructions": row.instructions,
        "qr_url": row.qr_url,
        "payment_url": row.payment_url,
        "status": row.status,
        "sort_order": row.sort_order,
    }


def _admin(row):
    result = _public(row)
    result["tenant_id"] = row.tenant_id
    result["public_identifier"] = row.public_identifier
    result["private_value"] = row.private_value
    result["created_at"] = row.created_at.isoformat()
    result["updated_at"] = row.updated_at.isoformat()
    return result


def _audit_safe(row):
    return {
        "id": str(row.id),
        "tenant_id": row.tenant_id,
        "provider": row.provider,
        "account_label": row.account_label,
        "account_type": row.account_type,
        "currency": row.currency,
        "display_name": row.display_name,
        "masked_account": row.masked_account,
        "public_identifier": row.public_identifier,
        "status": row.status,
        "sort_order": row.sort_order,
    }


async def _audit(s: AsyncSession, user, action: str, row, before=None):
    s.add(AdminAuditLog(
        id=uuid.uuid4(), actor=str(user.get("sub", "unknown")), action=action,
        table_name="payment_accounts", record_id=str(row.id),
        before=before, after=None if action == "delete" else _audit_safe(row),
        created_at=datetime.utcnow(),
    ))


@router.get("/public")
async def public_payment_accounts(s: AsyncSession = Depends(db)):
    result = await s.execute(
        select(PaymentAccount)
        .where(PaymentAccount.tenant_id == "default", PaymentAccount.status == "active")
        .order_by(PaymentAccount.sort_order.asc(), PaymentAccount.created_at.asc())
    )
    return [_public(row) for row in result.scalars().all()]


@router.get("/admin")
async def list_payment_accounts(user=Depends(require_admin), s: AsyncSession = Depends(db)):
    tenant_id = None if "platform_admin" in set(user.get("roles", [])) else _tenant(user)
    stmt = select(PaymentAccount).order_by(PaymentAccount.sort_order.asc(), PaymentAccount.created_at.asc())
    if tenant_id:
        stmt = stmt.where(PaymentAccount.tenant_id == tenant_id)
    result = await s.execute(stmt)
    return [_admin(row) for row in result.scalars().all()]


@router.post("/admin", status_code=201)
async def create_payment_account(body: PaymentAccountIn, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    tenant_id = _tenant(user, body.tenant_id)
    now = datetime.utcnow()
    row = PaymentAccount(
        id=uuid.uuid4(), tenant_id=tenant_id, provider=body.provider.lower(),
        account_label=body.account_label, account_type=body.account_type,
        currency=body.currency.upper(), display_name=body.display_name,
        masked_account=body.masked_account, public_identifier=body.public_identifier,
        private_value=body.private_value, instructions=body.instructions,
        qr_url=body.qr_url, payment_url=body.payment_url, status=body.status,
        sort_order=body.sort_order, created_at=now, updated_at=now,
    )
    s.add(row)
    await _audit(s, user, "create", row)
    await s.commit()
    await s.refresh(row)
    return _admin(row)


@router.patch("/admin/{account_id}")
async def update_payment_account(account_id: str, body: PaymentAccountPatch, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    try:
        uid = uuid.UUID(account_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid payment account id") from exc
    stmt = select(PaymentAccount).where(PaymentAccount.id == uid)
    if "platform_admin" not in set(user.get("roles", [])):
        stmt = stmt.where(PaymentAccount.tenant_id == _tenant(user))
    row = (await s.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "payment account not found")
    before = _audit_safe(row)
    for key, value in body.model_dump(exclude_unset=True).items():
        if key == "provider" and value is not None:
            value = value.lower()
        if key == "currency" and value is not None:
            value = value.upper()
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    await _audit(s, user, "update", row, before=before)
    await s.commit()
    await s.refresh(row)
    return _admin(row)


@router.delete("/admin/{account_id}")
async def delete_payment_account(account_id: str, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    try:
        uid = uuid.UUID(account_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid payment account id") from exc
    stmt = select(PaymentAccount).where(PaymentAccount.id == uid)
    if "platform_admin" not in set(user.get("roles", [])):
        stmt = stmt.where(PaymentAccount.tenant_id == _tenant(user))
    row = (await s.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "payment account not found")
    before = _audit_safe(row)
    await _audit(s, user, "delete", row, before=before)
    await s.delete(row)
    await s.commit()
    return {"ok": True, "id": account_id}
