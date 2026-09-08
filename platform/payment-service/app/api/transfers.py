from decimal import Decimal

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import PaymentMethod, Transaction, TxStatus, TxType, Wallet
from app.schemas.schemas import TransferIn, TxOut
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("", response_model=TxOut, status_code=201)
async def internal_transfer(body: TransferIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    if body.to_user_id == user["sub"]:
        raise HTTPException(400, "cannot transfer to the same user")
    currency = body.currency.upper()
    amount = Decimal(str(body.amount))
    if amount <= 0:
        raise HTTPException(400, "amount must be greater than zero")
    reference = body.note if body.note and body.note.startswith("work:") else None

    if reference:
        existing = await s.scalar(
            select(Transaction).where(
                Transaction.user_id == user["sub"],
                Transaction.type == TxType.transfer,
                Transaction.reference == reference,
                Transaction.status == TxStatus.completed,
            )
        )
        if existing:
            return TxOut(id=str(existing.id), type=existing.type, method=existing.method, status=existing.status,
                         amount=float(existing.amount), fee=float(existing.fee), currency=existing.currency,
                         reference=existing.reference, created_at=existing.created_at.isoformat(),
                         completed_at=existing.completed_at.isoformat() if existing.completed_at else None)

    users = sorted([user["sub"], body.to_user_id])
    wallets = {}
    for uid in users:
        wallet = await s.scalar(
            select(Wallet).where(Wallet.user_id == uid, Wallet.currency == currency).with_for_update()
        )
        if not wallet:
            if uid != body.to_user_id:
                raise HTTPException(404, "source wallet not found")
            wallet = Wallet(tenant_id=user.get("tenant_id", "default"), user_id=uid, currency=currency, balance=0)
            s.add(wallet)
            await s.flush()
        wallets[uid] = wallet

    src = wallets[user["sub"]]
    dst = wallets[body.to_user_id]
    available = Decimal(str(src.balance)) - Decimal(str(src.frozen))
    if available < amount:
        raise HTTPException(400, "insufficient available funds")

    src.balance = Decimal(str(src.balance)) - amount
    dst.balance = Decimal(str(dst.balance)) + amount
    src_tx = Transaction(
        tenant_id=user.get("tenant_id", "default"), user_id=user["sub"], wallet_id=src.id,
        type=TxType.transfer, method=PaymentMethod.transfer, status=TxStatus.completed,
        amount=-amount, currency=currency, fee=0, reference=reference,
        meta={"to": body.to_user_id, "note": body.note},
    )
    dst_tx = Transaction(
        tenant_id=user.get("tenant_id", "default"), user_id=body.to_user_id, wallet_id=dst.id,
        type=TxType.transfer, method=PaymentMethod.transfer, status=TxStatus.completed,
        amount=amount, currency=currency, fee=0, reference=reference,
        meta={"from": user["sub"], "note": body.note},
    )
    s.add_all([src_tx, dst_tx])
    await s.commit()
    return TxOut(id=str(src_tx.id), type=src_tx.type, method=src_tx.method, status=src_tx.status,
                 amount=float(src_tx.amount), fee=0, currency=src_tx.currency, reference=src_tx.reference,
                 created_at=src_tx.created_at.isoformat(), completed_at=src_tx.created_at.isoformat())
