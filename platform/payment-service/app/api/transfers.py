from decimal import Decimal

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Transaction, TxStatus, TxType, Wallet
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
    try:
        user = await verify_token(creds.credentials)
    except ValueError as exc:
        raise HTTPException(401, "invalid or expired authentication token") from exc
    if not user.get("sub"):
        raise HTTPException(401, "authentication subject missing")
    return user


@router.post("", response_model=TxOut, status_code=201)
async def internal_transfer(
    body: TransferIn, user=Depends(current_user), s: AsyncSession = Depends(db)
):
    tenant_id = user.get("tenant_id", "default")
    currency = body.currency.upper()
    if body.to_user_id == user["sub"]:
        raise HTTPException(400, "cannot transfer to yourself")

    res = await s.execute(
        select(Wallet).where(
            Wallet.tenant_id == tenant_id,
            Wallet.user_id == user["sub"],
            Wallet.currency == currency,
        ).with_for_update()
    )
    src = res.scalar_one_or_none()
    if not src:
        raise HTTPException(404, "source wallet not found")
    if Decimal(str(src.balance)) < Decimal(str(body.amount)):
        raise HTTPException(400, "insufficient funds")

    res = await s.execute(
        select(Wallet).where(
            Wallet.tenant_id == tenant_id,
            Wallet.user_id == body.to_user_id,
            Wallet.currency == currency,
        ).with_for_update()
    )
    dst = res.scalar_one_or_none()
    if not dst:
        dst = Wallet(tenant_id=tenant_id, user_id=body.to_user_id, currency=currency, balance=0)
        s.add(dst)
        await s.flush()

    amount = Decimal(str(body.amount))
    src.balance = Decimal(str(src.balance)) - amount
    dst.balance = Decimal(str(dst.balance)) + amount
    tx = Transaction(
        tenant_id=tenant_id,
        user_id=user["sub"],
        wallet_id=src.id,
        type=TxType.transfer,
        method="transfer",
        status=TxStatus.completed,
        amount=amount,
        currency=currency,
        fee=0,
        meta={"to": body.to_user_id, "note": body.note},
    )
    s.add(tx)
    await s.commit()
    return TxOut(
        id=str(tx.id), type=tx.type, method=tx.method, status=tx.status,
        amount=float(tx.amount), fee=0, currency=tx.currency, reference=None,
        created_at=tx.created_at.isoformat(), completed_at=tx.created_at.isoformat(),
    )
