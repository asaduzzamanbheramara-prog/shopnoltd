import uuid
from datetime import datetime
from decimal import Decimal

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Transaction, TxStatus, TxType, Wallet
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def require_admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        user = await verify_token(creds.credentials)
    except ValueError as exc:
        raise HTTPException(401, "invalid or expired authentication token") from exc
    roles = user.get("roles", [])
    if "platform_admin" not in roles and "admin" not in roles:
        raise HTTPException(403, "admin only")
    return user


@router.get("/pending")
async def pending(user=Depends(require_admin), s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(Transaction).where(
            Transaction.tenant_id == user.get("tenant_id", "default"),
            Transaction.status.in_([TxStatus.requires_approval, TxStatus.pending]),
        )
    )
    return [
        {
            "id": str(t.id), "type": t.type.value, "method": t.method.value,
            "amount": float(t.amount), "currency": t.currency,
            "created_at": t.created_at.isoformat(),
        }
        for t in res.scalars().all()
    ]


@router.post("/approve/{tx_id}")
async def approve(tx_id: str, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    try:
        transaction_id = uuid.UUID(tx_id)
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(400, "invalid transaction id") from exc

    tenant_id = user.get("tenant_id", "default")
    res = await s.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.tenant_id == tenant_id,
        ).with_for_update()
    )
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "tx not found")
    if tx.status not in (TxStatus.requires_approval, TxStatus.pending):
        raise HTTPException(400, "tx not pending approval")
    wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update())
    w = wr.scalar_one_or_none()
    if not w or w.tenant_id != tenant_id:
        raise HTTPException(409, "wallet ownership mismatch")

    amount = Decimal(str(tx.amount))
    fee = Decimal(str(tx.fee))
    if tx.type == TxType.withdrawal:
        if Decimal(str(w.frozen)) < amount or Decimal(str(w.balance)) < amount + fee:
            raise HTTPException(409, "insufficient reserved funds")
        w.balance = Decimal(str(w.balance)) - amount - fee
        w.frozen = max(Decimal("0"), Decimal(str(w.frozen)) - amount)
    elif tx.type == TxType.deposit or tx.type == TxType.refund:
        w.balance = Decimal(str(w.balance)) + amount - fee
    else:
        raise HTTPException(400, "manual approval is not supported for this transaction type")

    tx.status = TxStatus.completed
    tx.completed_at = datetime.utcnow()
    tx.approved_by = user["sub"]
    await s.commit()
    return {"ok": True}


@router.post("/reject/{tx_id}")
async def reject(tx_id: str, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    try:
        transaction_id = uuid.UUID(tx_id)
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(400, "invalid transaction id") from exc

    tenant_id = user.get("tenant_id", "default")
    res = await s.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.tenant_id == tenant_id,
        ).with_for_update()
    )
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "tx not found")
    if tx.status not in (TxStatus.requires_approval, TxStatus.pending):
        raise HTTPException(400, "tx not pending approval")
    if tx.type == TxType.withdrawal:
        wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update())
        w = wr.scalar_one_or_none()
        if w and w.tenant_id == tenant_id:
            w.frozen = max(Decimal("0"), Decimal(str(w.frozen)) - Decimal(str(tx.amount)))
    tx.status = TxStatus.cancelled
    tx.completed_at = datetime.utcnow()
    tx.approved_by = user["sub"]
    await s.commit()
    return {"ok": True}
