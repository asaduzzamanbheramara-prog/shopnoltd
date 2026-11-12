import hashlib
from decimal import Decimal

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.core.tenant import require_tenant_id
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


def _destination_fingerprint(destination: str) -> str:
    return hashlib.sha256(destination.strip().encode("utf-8")).hexdigest()


def _validate_existing_withdrawal(existing: Transaction, body: WithdrawalIn, currency: str, amount: Decimal) -> None:
    meta = existing.meta or {}
    if (
        Decimal(str(existing.amount)) != amount
        or existing.currency.upper() != currency
        or existing.method != body.method
        or meta.get("destination_sha256") != _destination_fingerprint(body.destination)
    ):
        raise HTTPException(409, "Idempotency key was already used for a different withdrawal")


def _withdrawal_out(tx: Transaction, approval_url: str | None = None) -> TxOut:
    return TxOut(
        id=str(tx.id), type=tx.type, method=tx.method, status=tx.status,
        amount=float(tx.amount), fee=float(tx.fee), currency=tx.currency,
        reference=tx.external_id, created_at=tx.created_at.isoformat(),
        completed_at=tx.completed_at.isoformat() if tx.completed_at else None,
        approval_url=approval_url,
    )


@router.post("", response_model=TxOut, status_code=201)
async def create_withdrawal(body: WithdrawalIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    amount = Decimal(str(body.amount))
    if not amount.is_finite() or amount < settings.min_withdrawal or amount > settings.max_withdrawal:
        raise HTTPException(400, "amount out of range")
    currency = body.currency.upper().strip()
    tenant_id = require_tenant_id(user)
    user_id = user["sub"]
    existing_query = select(Transaction).where(
        Transaction.tenant_id == tenant_id,
        Transaction.user_id == user_id,
        Transaction.type == TxType.withdrawal,
        Transaction.idempotency_key == body.idempotency_key,
    )
    existing = await s.scalar(existing_query)
    if existing:
        _validate_existing_withdrawal(existing, body, currency, amount)
        return _withdrawal_out(existing)

    try:
        provider = get_provider(body.method)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if hasattr(provider, "enabled") and not provider.enabled:
        raise HTTPException(503, f"Payment provider '{body.method.value}' is not configured")

    # Lock the wallet, then recheck the idempotency key inside the lock. The
    # unique transaction index remains the final guard for concurrent retries.
    res = await s.execute(
        select(Wallet).where(
            Wallet.tenant_id == tenant_id,
            Wallet.user_id == user_id,
            Wallet.currency == currency,
        ).with_for_update()
    )
    wallet = res.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(404, "wallet not found")
    existing = await s.scalar(existing_query)
    if existing:
        _validate_existing_withdrawal(existing, body, currency, amount)
        await s.rollback()
        return _withdrawal_out(existing)

    fee = amount * Decimal(str(settings.platform_fee_pct)) / Decimal("100")
    reserved_amount = amount + fee
    available = Decimal(str(wallet.balance)) - Decimal(str(wallet.frozen))
    if available < reserved_amount:
        raise HTTPException(400, "insufficient available funds including withdrawal fee")

    wallet.frozen = Decimal(str(wallet.frozen)) + reserved_amount
    tx = Transaction(
        tenant_id=tenant_id,
        user_id=user_id,
        wallet_id=wallet.id,
        type=TxType.withdrawal,
        method=body.method,
        status=TxStatus.requires_approval if settings.admin_approval_required else TxStatus.processing,
        amount=amount,
        currency=currency,
        fee=fee,
        idempotency_key=body.idempotency_key,
        meta={**(body.metadata or {}), "destination_sha256": _destination_fingerprint(body.destination)},
    )
    s.add(tx)
    try:
        # Persist the reservation and stable transaction ID before calling an
        # external provider. A retry can return this same record, never create
        # a second payout after an ambiguous network timeout.
        await s.commit()
    except Exception:
        await s.rollback()
        existing = await s.scalar(existing_query)
        if existing:
            _validate_existing_withdrawal(existing, body, currency, amount)
            return _withdrawal_out(existing)
        raise

    try:
        out = await provider.create_withdrawal(tx, destination=body.destination, idempotency_key=body.idempotency_key)
    except NotImplementedError:
        # No payout was initiated by an unsupported provider: safely release
        # the reservation and mark this idempotency record terminal.
        wallet = await s.scalar(select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update())
        if wallet:
            wallet.frozen = max(Decimal("0"), Decimal(str(wallet.frozen)) - amount)
        tx.status = TxStatus.failed
        await s.commit()
        raise HTTPException(400, "withdrawal is not supported by this payment method") from None
    except Exception:
        # The provider may have accepted the payout before the connection
        # failed. Keep funds frozen and the stable transaction for manual
        # reconciliation; never automatically issue a second payout.
        raise HTTPException(502, "withdrawal provider outcome is pending reconciliation") from None

    tx.status = TxStatus.requires_approval if out.get("status") == "requires_approval" else TxStatus.processing
    tx.external_id = out.get("external_id")
    await s.commit()
    return _withdrawal_out(tx, out.get("approval_url"))
