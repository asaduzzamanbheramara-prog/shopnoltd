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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


def tx_out(tx: Transaction) -> TxOut:
    meta = tx.meta or {}
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
        redirect_url=meta.get("_redirect_url"),
        qr_code=meta.get("_qr_code"),
        address=meta.get("_address"),
        approval_url=meta.get("_approval_url"),
    )


@router.post("", response_model=TxOut, status_code=201)
async def create_deposit(body: DepositIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    currency = body.currency.upper()
    tenant_id = user.get("tenant_id", "default")
    user_id = user["sub"]

    if body.amount < settings.min_deposit or body.amount > settings.max_deposit:
        raise HTTPException(400, "amount out of range")
    try:
        provider = get_provider(body.method)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not supports_deposit(body.method, currency):
        raise HTTPException(400, f"Payment method '{body.method.value}' does not support deposits in {currency}")
    if hasattr(provider, "enabled") and not provider.enabled:
        raise HTTPException(503, f"Payment provider '{body.method.value}' is not configured")

    # Idempotency is enforced by a database uniqueness constraint. Return the
    # original transaction for retries instead of creating another provider
    # payment. This is intentionally checked before any external side effect.
    existing = await s.scalar(
        select(Transaction).where(
            Transaction.tenant_id == tenant_id,
            Transaction.user_id == user_id,
            Transaction.type == TxType.deposit,
            Transaction.idempotency_key == body.idempotency_key,
        )
    )
    if existing:
        return tx_out(existing)

    res = await s.execute(
        select(Wallet).where(Wallet.user_id == user_id, Wallet.currency == currency)
    )
    w = res.scalar_one_or_none()
    if not w:
        w = Wallet(tenant_id=tenant_id, user_id=user_id, currency=currency, balance=0)
        s.add(w)
        await s.flush()

    tx = Transaction(
        tenant_id=tenant_id,
        user_id=user_id,
        wallet_id=w.id,
        type=TxType.deposit,
        method=body.method,
        status=TxStatus.pending,
        amount=body.amount,
        fee=0,
        currency=currency,
        idempotency_key=body.idempotency_key,
        meta=body.metadata or {},
    )
    s.add(tx)
    await s.flush()

    try:
        # Persist the transaction before crossing the external-provider
        # boundary. If the worker dies after this point, a retry sees the same
        # idempotency record instead of creating a second payment.
        await s.commit()
    except IntegrityError:
        await s.rollback()
        existing = await s.scalar(
            select(Transaction).where(
                Transaction.tenant_id == tenant_id,
                Transaction.user_id == user_id,
                Transaction.type == TxType.deposit,
                Transaction.idempotency_key == body.idempotency_key,
            )
        )
        if existing:
            return tx_out(existing)
        raise HTTPException(409, "deposit idempotency conflict")

    try:
        out = await provider.create_deposit(
            tx,
            return_url=body.return_url,
            idempotency_key=body.idempotency_key,
        )
    except NotImplementedError as exc:
        tx.status = TxStatus.failed
        tx.meta = {**(tx.meta or {}), "_error": str(exc)}
        await s.commit()
        raise HTTPException(400, str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        tx.status = TxStatus.failed
        tx.meta = {**(tx.meta or {}), "_error": str(exc)}
        await s.commit()
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        tx.status = TxStatus.failed
        tx.meta = {**(tx.meta or {}), "_error": "payment provider request failed"}
        await s.commit()
        raise HTTPException(502, "payment provider request failed") from exc

    if out.get("status") in {"failed", "unavailable"}:
        tx.status = TxStatus.failed
        tx.meta = {
            **(tx.meta or {}),
            "_error": out.get("note") or "Payment provider is unavailable",
        }
        await s.commit()
        raise HTTPException(503, out.get("note") or "Payment provider is unavailable")

    tx.external_id = out.get("external_id")
    tx.meta = {
        **(tx.meta or {}),
        **{key: out[key] for key in ("redirect_url", "qr_code", "address", "approval_url") if out.get(key)},
    }
    await s.commit()
    return tx_out(tx)


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
    return tx_out(tx)
