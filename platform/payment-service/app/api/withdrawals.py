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
    try:
        user = await verify_token(creds.credentials)
    except ValueError as exc:
        raise HTTPException(401, "invalid or expired authentication token") from exc
    if not user.get("sub"):
        raise HTTPException(401, "authentication subject missing")
    return user


@router.post("", response_model=TxOut, status_code=201)
async def create_withdrawal(
    body: WithdrawalIn, user=Depends(current_user), s: AsyncSession = Depends(db)
):
    currency = body.currency.upper()
    tenant_id = user.get("tenant_id", "default")
    if body.amount < settings.min_withdrawal or body.amount > settings.max_withdrawal:
        raise HTTPException(400, "amount out of range")
    fee = Decimal(str(body.amount)) * Decimal(str(settings.platform_fee_pct)) / Decimal("100")
    total = Decimal(str(body.amount)) + fee
    res = await s.execute(
        select(Wallet).where(
            Wallet.tenant_id == tenant_id,
            Wallet.user_id == user["sub"],
            Wallet.currency == currency,
        )
    )
    w = res.scalar_one_or_none()
    if not w:
        raise HTTPException(404, "wallet not found")
    if Decimal(str(w.balance)) < total:
        raise HTTPException(400, "insufficient funds")
    w.frozen = Decimal(str(w.frozen)) + Decimal(str(body.amount))
    tx = Transaction(
        tenant_id=tenant_id,
        user_id=user["sub"],
        wallet_id=w.id,
        type=TxType.withdrawal,
        method=body.method,
        status=TxStatus.requires_approval if settings.admin_approval_required else TxStatus.processing,
        amount=body.amount,
        currency=currency,
        fee=fee,
        meta=body.metadata,
    )
    s.add(tx)
    await s.flush()
    provider = get_provider(body.method)
    out = await provider.create_withdrawal(tx, destination=body.destination)
    tx.status = TxStatus.requires_approval if out.get("status") == "requires_approval" else TxStatus.processing
    tx.external_id = out.get("external_id")
    await s.commit()
    return TxOut(
        id=str(tx.id), type=tx.type, method=tx.method, status=tx.status,
        amount=float(tx.amount), fee=float(tx.fee), currency=tx.currency,
        reference=tx.external_id, created_at=tx.created_at.isoformat(), completed_at=None,
        approval_url=out.get("approval_url"),
    )
