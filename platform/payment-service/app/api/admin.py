import uuid
from datetime import datetime
from decimal import Decimal

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Transaction, TxStatus, Wallet
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
    if "admin" not in user.get("roles", []):
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
    res = await s.execute(select(Transaction).where(Transaction.id == uuid.UUID(tx_id)))
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "tx not found")
    if tx.status not in (TxStatus.requires_approval, TxStatus.pending):
        raise HTTPException(400, "tx not pending approval")
    wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id))
    w = wr.scalar_one()
    if tx.type.value == "withdrawal":
        w.balance = Decimal(str(w.balance)) - Decimal(str(tx.amount))
        w.frozen = Decimal(str(w.frozen)) - Decimal(str(tx.amount))
    tx.status = TxStatus.completed
    tx.completed_at = datetime.utcnow()
    tx.approved_by = user["sub"]
    await s.commit()
    return {"ok": True}


@router.post("/reject/{tx_id}")
async def reject(tx_id: str, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Transaction).where(Transaction.id == uuid.UUID(tx_id)))
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "tx not found")
    if tx.type.value == "withdrawal":
        wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id))
        w = wr.scalar_one()
        w.frozen = Decimal(str(w.frozen)) - Decimal(str(tx.amount))
    tx.status = TxStatus.cancelled
    tx.completed_at = datetime.utcnow()
    tx.approved_by = user["sub"]
    await s.commit()
    return {"ok": True}
