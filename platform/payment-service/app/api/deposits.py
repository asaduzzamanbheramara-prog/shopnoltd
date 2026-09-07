import uuid

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Transaction, TxStatus, TxType, Wallet
from app.providers.registry import get_provider, supports_deposit
from app.schemas.schemas import DepositIn, TxOut
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
async def create_deposit(
    body: DepositIn, user=Depends(current_user), s: AsyncSession = Depends(db)
):
    currency = body.currency.upper()
    if body.amount < settings.min_deposit or body.amount > settings.max_deposit:
        raise HTTPException(400, "amount out of range")

    try:
        provider = get_provider(body.method)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not supports_deposit(body.method, currency):
        raise HTTPException(
            400,
            f"Payment method '{body.method.value}' does not support deposits in {currency}",
        )

    if hasattr(provider, "enabled") and not provider.enabled:
        raise HTTPException(503, f"Payment provider '{body.method.value}' is not configured")

    res = await s.execute(
        select(Wallet).where(
            Wallet.user_id == user["sub"], Wallet.currency == currency
        )
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
        await s.flush()
    tx = Transaction(
        tenant_id=user.get("tenant_id", "default"),
        wallet_id=w.id,
        type=TxType.deposit,
        method=body.method,
        status=TxStatus.pending,
        amount=body.amount,
        fee=0,
        currency=currency,
        meta=body.metadata,
    )
    s.add(tx)
    await s.flush()
    try:
        out = await provider.create_deposit(tx, return_url=body.return_url)
    except NotImplementedError as exc:
        await s.rollback()
        raise HTTPException(400, str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        await s.rollback()
        raise HTTPException(503, str(exc)) from exc
    except Exception:
        await s.rollback()
        raise HTTPException(502, "payment provider request failed")

    tx.external_id = out.get("external_id")
    if out.get("status") in {"failed", "unavailable"}:
        await s.rollback()
        raise HTTPException(503, out.get("note") or f"Payment provider '{body.method.value}' is unavailable")
    await s.commit()
    return TxOut(
        id=str(tx.id),
        type=tx.type,
        method=tx.method,
        status=tx.status,
        amount=float(tx.amount),
        fee=0,
        currency=tx.currency,
        reference=tx.external_id,
        created_at=tx.created_at.isoformat(),
        completed_at=None,
        redirect_url=out.get("redirect_url"),
        qr_code=out.get("qr_code"),
        address=out.get("address"),
        approval_url=out.get("approval_url"),
    )


@router.get("/{tx_id}", response_model=TxOut)
async def get_deposit(tx_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    try:
        transaction_id = uuid.UUID(tx_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid transaction id") from exc

    res = await s.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.tenant_id == user.get("tenant_id", "default"),
            Transaction.user_id == user["sub"],
        )
    )
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(404, "tx not found")
    return TxOut(
        id=str(tx.id),
        type=tx.type,
        method=tx.method,
        status=tx.status,
        amount=float(tx.amount),
        fee=float(tx.fee),
        currency=tx.currency,
        reference=tx.external_id,
        created_at=tx.created_at.isoformat(),
        completed_at=tx.completed_at.isoformat() if tx.completed_at else None,
    )
