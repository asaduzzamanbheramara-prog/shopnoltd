from decimal import Decimal

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Transaction, TxStatus, TxType, Wallet
from app.providers.registry import get_provider
from app.schemas.schemas import TxOut, WithdrawalIn
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
async def create_withdrawal(body: WithdrawalIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    if body.amount < settings.min_withdrawal or body.amount > settings.max_withdrawal:
        raise HTTPException(400, "amount out of range")
    currency = body.currency.upper()
    try:
        provider = get_provider(body.method)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if hasattr(provider, "enabled") and not provider.enabled:
        raise HTTPException(503, f"Payment provider '{body.method.value}' is not configured")

    # Serialize withdrawals for the same wallet so concurrent requests cannot
    # both observe the same available balance and over-reserve funds.
    res = await s.execute(
        select(Wallet)
        .where(Wallet.user_id == user["sub"], Wallet.currency == currency)
        .with_for_update()
    )
    w = res.scalar_one_or_none()
    if not w:
        raise HTTPException(404, "wallet not found")
    amount = Decimal(str(body.amount))
    balance = Decimal(str(w.balance))
    frozen = Decimal(str(w.frozen))
    if balance - frozen < amount:
        raise HTTPException(400, "insufficient available funds")

    w.frozen = frozen + amount
    tx = Transaction(
        tenant_id=user.get("tenant_id", "default"), user_id=user["sub"], wallet_id=w.id,
        type=TxType.withdrawal, method=body.method,
        status=TxStatus.requires_approval if settings.admin_approval_required else TxStatus.processing,
        amount=body.amount, currency=currency, fee=amount * settings.platform_fee_pct / 100,
        meta=body.metadata,
    )
    s.add(tx)
    await s.flush()
    try:
        out = await provider.create_withdrawal(tx, destination=body.destination)
    except NotImplementedError as exc:
        await s.rollback(); raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        await s.rollback(); raise HTTPException(502, "withdrawal provider request failed") from exc
    tx.status = TxStatus.requires_approval if out.get("status") == "requires_approval" else TxStatus.processing
    tx.external_id = out.get("external_id")
    await s.commit()
    return TxOut(id=str(tx.id), type=tx.type, method=tx.method, status=tx.status, amount=float(tx.amount), fee=float(tx.fee),
                 currency=tx.currency, reference=tx.external_id, created_at=tx.created_at.isoformat(), completed_at=None,
                 approval_url=out.get("approval_url"))
