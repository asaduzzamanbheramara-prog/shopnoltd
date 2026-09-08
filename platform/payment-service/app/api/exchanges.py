from decimal import Decimal
import uuid

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import PaymentMethod, Transaction, TxStatus, TxType, Wallet
from app.providers.exchange_client import convert, get_rate
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


class RateOut(BaseModel):
    from_currency: str
    to_currency: str
    rate: float
    timestamp: str


@router.get("/rate", response_model=RateOut)
async def rate(from_currency: str, to_currency: str, user=Depends(current_user)):
    r = await get_rate(from_currency.upper(), to_currency.upper())
    return RateOut(
        from_currency=from_currency.upper(),
        to_currency=to_currency.upper(),
        rate=r["rate"],
        timestamp=r["timestamp"],
    )


class ConvertIn(BaseModel):
    from_currency: str
    to_currency: str
    amount: float = Field(gt=0)
    idempotency_key: str = Field(min_length=8, max_length=128)


class ConvertOut(BaseModel):
    from_amount: float
    to_amount: float
    rate: float
    fee: float
    from_currency: str
    to_currency: str
    reference: str
    transaction_id: str


@router.post("/convert", response_model=ConvertOut)
async def do_convert(body: ConvertIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    frm = body.from_currency.upper().strip()
    to = body.to_currency.upper().strip()
    if frm == to:
        raise HTTPException(400, "source and destination currencies must differ")

    reference = f"exchange:{body.idempotency_key}"
    existing = await s.scalar(
        select(Transaction).where(
            Transaction.user_id == user["sub"],
            Transaction.type == TxType.exchange,
            Transaction.reference == reference,
            Transaction.status == TxStatus.completed,
        )
    )
    if existing:
        meta = existing.meta or {}
        return ConvertOut(
            from_amount=float(meta["from_amount"]),
            to_amount=float(meta["to_amount"]),
            rate=float(meta["rate"]),
            fee=float(existing.fee),
            from_currency=frm,
            to_currency=to,
            reference=reference,
            transaction_id=str(existing.id),
        )

    try:
        converted = await convert(frm, to, body.amount)
    except Exception as exc:
        raise HTTPException(502, f"Exchange provider unavailable: {exc}") from exc

    from_amount = Decimal(str(converted["from_amount"]))
    to_amount = Decimal(str(converted["to_amount"]))
    fee = Decimal(str(converted.get("fee", 0)))
    rate_value = Decimal(str(converted["rate"]))
    if from_amount <= 0 or to_amount <= 0 or rate_value <= 0 or fee < 0:
        raise HTTPException(502, "Exchange provider returned an invalid conversion")

    # Lock both wallets in deterministic order so concurrent exchanges cannot
    # overspend a wallet or deadlock each other. The entire debit/credit and
    # both immutable ledger entries are one database transaction.
    user_id = user["sub"]
    wallets = {}
    for currency in sorted([frm, to]):
        wallet = await s.scalar(
            select(Wallet)
            .where(Wallet.user_id == user_id, Wallet.currency == currency)
            .with_for_update()
        )
        if not wallet:
            if currency == to:
                wallet = Wallet(
                    tenant_id=user.get("tenant_id", "default"),
                    user_id=user_id,
                    currency=currency,
                    balance=0,
                )
                s.add(wallet)
                await s.flush()
            else:
                raise HTTPException(404, f"{frm} wallet not found")
        wallets[currency] = wallet

    source = wallets[frm]
    destination = wallets[to]
    available = Decimal(str(source.balance)) - Decimal(str(source.frozen))
    total_debit = from_amount + fee
    if available < total_debit:
        raise HTTPException(400, f"insufficient available {frm} funds")

    source.balance = Decimal(str(source.balance)) - total_debit
    destination.balance = Decimal(str(destination.balance)) + to_amount

    meta = {
        "from_amount": str(from_amount),
        "to_amount": str(to_amount),
        "rate": str(rate_value),
        "from_currency": frm,
        "to_currency": to,
    }
    source_tx = Transaction(
        tenant_id=user.get("tenant_id", "default"),
        user_id=user_id,
        wallet_id=source.id,
        type=TxType.exchange,
        method=PaymentMethod.manual,
        status=TxStatus.completed,
        amount=-from_amount,
        currency=frm,
        fee=fee,
        reference=reference,
        meta=meta,
    )
    destination_tx = Transaction(
        tenant_id=user.get("tenant_id", "default"),
        user_id=user_id,
        wallet_id=destination.id,
        type=TxType.exchange,
        method=PaymentMethod.manual,
        status=TxStatus.completed,
        amount=to_amount,
        currency=to,
        fee=0,
        reference=reference,
        meta=meta,
    )
    s.add_all([source_tx, destination_tx])
    await s.commit()

    return ConvertOut(
        from_amount=float(from_amount),
        to_amount=float(to_amount),
        rate=float(rate_value),
        fee=float(fee),
        from_currency=frm,
        to_currency=to,
        reference=reference,
        transaction_id=str(source_tx.id),
    )
