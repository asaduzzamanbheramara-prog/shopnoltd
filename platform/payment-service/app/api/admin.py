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
    user = await verify_token(creds.credentials)
    if not ({"platform_admin", "admin"} & set(user.get("roles", []))):
        raise HTTPException(403, "admin only")
    return user


@router.get("/pending")
async def pending(user=Depends(require_admin), s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(Transaction).where(
            Transaction.status.in_([TxStatus.requires_approval, TxStatus.pending])
        )
    )
    return [
        {
            "id": str(t.id),
            "type": t.type.value,
            "method": t.method.value,
            "amount": float(t.amount),
            "currency": t.currency,
            "created_at": t.created_at.isoformat(),
        }
        for t in res.scalars().all()
    ]


@router.post("/approve/{tx_id}")
async def approve(tx_id: str, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    try:
        transaction_id = uuid.UUID(tx_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(400, "invalid transaction id") from exc

    res = await s.execute(
        select(Transaction).where(Transaction.id == transaction_id).with_for_update()
    )
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "tx not found")
    if tx.status not in (TxStatus.requires_approval, TxStatus.pending):
        raise HTTPException(400, "tx not pending approval")

    wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update())
    w = wr.scalar_one_or_none()
    if not w:
        raise HTTPException(409, "transaction wallet missing")

    # Approval is authorization, not proof that an external payout or deposit
    # has settled. Do not mutate wallet balances or mark a withdrawal completed
    # here; this service does not yet have a durable, idempotent payout dispatcher.
    if tx.type == TxType.withdrawal:
        raise HTTPException(
            503,
            "withdrawal approval is temporarily blocked until an idempotent payout dispatcher is configured",
        )
    if tx.type != TxType.deposit:
        raise HTTPException(400, "this transaction type cannot be approved here")

    tx.approved_by = user["sub"]
    tx.status = TxStatus.processing
    await s.commit()
    return {"ok": True, "status": "processing"}


@router.post("/reject/{tx_id}")
async def reject(tx_id: str, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    try:
        transaction_id = uuid.UUID(tx_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(400, "invalid transaction id") from exc

    res = await s.execute(
        select(Transaction).where(Transaction.id == transaction_id).with_for_update()
    )
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "tx not found")
    if tx.status not in (TxStatus.requires_approval, TxStatus.pending):
        raise HTTPException(400, "tx not pending approval")

    if tx.type == tx.type.withdrawal:
        wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update())
        w = wr.scalar_one_or_none()
        if not w:
            raise HTTPException(409, "transaction wallet missing")
        amount = Decimal(str(tx.amount))
        frozen = Decimal(str(w.frozen))
        if frozen < amount:
            raise HTTPException(409, "withdrawal reservation is inconsistent")
        w.frozen = frozen - amount

    tx.status = TxStatus.cancelled
    tx.completed_at = datetime.utcnow()
    tx.approved_by = user["sub"]
    await s.commit()
    return {"ok": True}
