"""Wallet endpoints — full replacement for app/api/wallets.py.

Two changes from the original:
1. get_wallet no longer 404s when a user has no wallet row yet for a
   currency — it creates a zero-balance one on first access. This is
   the direct fix for "error when currency change": switching to a
   currency you've never held silently 404'd before.
2. Added GET /{currency}/ledger, which the frontend already calls
   (getWalletLedger) but which never existed on the backend. There's
   no separate ledger table, so this derives a running balance from
   completed transactions against the wallet, newest first — matching
   the sign convention already used in admin.py (deposit: +amount,
   withdrawal: -amount).
"""

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Transaction, TxStatus, Wallet
from app.schemas.schemas import WalletOut
from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.get("", response_model=list[WalletOut])
async def list_wallets(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"]))
    return res.scalars().all()


@router.get("/{currency}", response_model=WalletOut)
async def get_wallet(currency: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
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
            frozen=0,
        )
        s.add(w)
        try:
            await s.commit()
        except Exception:
            # Another request created it concurrently (unique index on
            # user_id+currency) — fetch the row that won instead of erroring.
            await s.rollback()
            res = await s.execute(
                select(Wallet).where(Wallet.user_id == user["sub"], Wallet.currency == currency)
            )
            w = res.scalar_one()
        else:
            await s.refresh(w)
    return w


@router.get("/{currency}/ledger")
async def get_wallet_ledger(
    currency: str,
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
    limit: int = Query(50, le=200),
):
    currency = currency.upper()
    wres = await s.execute(
        select(Wallet).where(Wallet.user_id == user["sub"], Wallet.currency == currency)
    )
    w = wres.scalar_one_or_none()
    if not w:
        # No wallet yet == no history yet. Empty ledger, not an error.
        return []

    tres = await s.execute(
        select(Transaction)
        .where(Transaction.wallet_id == w.id, Transaction.status == TxStatus.completed)
        .order_by(Transaction.created_at.asc())
    )
    txs = tres.scalars().all()

    running = 0.0
    entries = []
    for t in txs:
        amount = float(t.amount)
        if t.type.value == "withdrawal":
            amount = -amount
        running += amount
        entries.append(
            {
                "id": str(t.id),
                "created_at": t.completed_at.isoformat() if t.completed_at else t.created_at.isoformat(),
                "entry_type": t.type.value,
                "amount": amount,
                "balance_after": round(running, 8),
                "reason": t.reference or t.method.value,
            }
        )

    entries.reverse()  # newest first, matching the transactions view
    return entries[:limit]
