from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Transaction, Wallet
from app.schemas.schemas import WalletOut
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.get("", response_model=list[WalletOut])
async def list_wallets(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"]))
    return res.scalars().all()


@router.get("/{currency}", response_model=WalletOut)
async def get_wallet(currency: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    """Auto-provision a zero-balance wallet instead of 404ing."""
    currency = currency.upper()
    res = await s.execute(
        select(Wallet).where(Wallet.user_id == user["sub"], Wallet.currency == currency)
    )
    w = res.scalar_one_or_none()
    if not w:
        w = Wallet(
            tenant_id=user.get("tenant_id", "default"),
            user_id=user["sub"],
            currency=currency,
            balance=0,
        )
        s.add(w)
        await s.commit()
        await s.refresh(w)
    return w


@router.get("/{currency}/ledger")
async def get_wallet_ledger(
    currency: str,
    limit: int = Query(50, ge=1, le=200),
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
):
    """Derive ledger entries from transactions; payment-service has no separate ledger table."""
    currency = currency.upper()
    res = await s.execute(
        select(Transaction)
        .join(Wallet, Wallet.id == Transaction.wallet_id)
        .where(Wallet.user_id == user["sub"], Transaction.currency == currency)
        .order_by(desc(Transaction.created_at))
        .limit(limit)
    )
    return [
        {
            "id": str(t.id),
            "type": t.type,
            "method": t.method,
            "status": t.status,
            "amount": float(t.amount),
            "fee": float(t.fee or 0),
            "currency": t.currency,
            "created_at": t.created_at.isoformat(),
        }
        for t in res.scalars().all()
    ]
