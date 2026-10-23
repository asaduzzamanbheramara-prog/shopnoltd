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
async def create_withdrawal(
    body: WithdrawalIn,
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
):
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
        .where(
            Wallet.tenant_id == user.get("tenant_id", "default"),
            Wallet.user_id == user["sub"],
            Wallet.currency == currency,
        )
        .with_for_update()
    )
    wallet = res.scalar_one_or_none()
    if not wallet:
        raise HTTPException(404, "wallet not found")

    amount = Decimal(str(body.amount))
    balance = Decimal(str(wallet.balance))
    frozen = Decimal(str(wallet.frozen))
    if balance - frozen < amount:
        raise HTTPException(400, "insufficient available funds")

    # Do not call a payout provider before configured administrator approval.
    # Persist the destination for the approval workflow; never claim a payout
    # completed merely because it was requested.
    if settings.admin_approval_required:
        wallet.frozen = frozen + amount
        tx = Transaction(
            tenant_id=user.get("tenant_id", "default"),
            user_id=user["sub"],
            wallet_id=wallet.id,
            type=TxType.withdrawal,
            method=body.method,
            status=TxStatus.requires_approval,
            amount=amount,
            currency=currency,
            fee=amount * Decimal(str(settings.platform_fee_pct)) / Decimal("100"),
            meta={**body.metadata, "withdrawal_destination": body.destination},
        )
        s.add(tx)
        await s.commit()
        await s.refresh(tx)
        return TxOut(
            id=str(tx.id), type=tx.type, method=tx.method, status=tx.status,
            amount=float(tx.amount), fee=float(tx.fee), currency=tx.currency,
            reference=None, created_at=tx.created_at.isoformat(), completed_at=None,
        )

    # Automatic payouts are only permitted when approval is explicitly disabled.
    wallet.frozen = frozen + amount
    tx = Transaction(
        tenant_id=user.get("tenant_id", "default"),
        user_id=user["sub"],
        wallet_id=wallet.id,
        type=TxType.withdrawal,
        method=body.method,
        status=TxStatus.processing,
        amount=amount,
        currency=currency,
        fee=amount * Decimal(str(settings.platform_fee_pct)) / Decimal("100"),
        meta=body.metadata,
    )
    s.add(tx)
    await s.flush()
    try:
        out = await provider.create_withdrawal(tx, destination=body.destination)
    except NotImplementedError as exc:
        await s.rollback()
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        await s.rollback()
        raise HTTPException(502, "withdrawal provider request failed") from exc

    tx.external_id = out.get("external_id")
    # Provider acceptance is not settlement. A signed success webhook must
    # perform the final balance debit and frozen-fund release.
    tx.status = TxStatus.processing
    await s.commit()
    return TxOut(
        id=str(tx.id), type=tx.type, method=tx.method, status=tx.status,
        amount=float(tx.amount), fee=float(tx.fee), currency=tx.currency,
        reference=tx.external_id, created_at=tx.created_at.isoformat(),
        completed_at=None, approval_url=out.get("approval_url"),
    )
