"""Internal, idempotent escrow operations for funded Work Marketplace tasks.

Funds remain in the creator wallet balance but are marked frozen until a
worker/platform payout or unused-budget release. Every movement is committed
atomically with its transaction journal entries.
"""
from datetime import datetime
from decimal import Decimal
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import require_work_escrow_key
from app.models.models import PaymentMethod, Transaction, TxStatus, TxType, Wallet

router = APIRouter(dependencies=[Depends(require_work_escrow_key)])


async def db():
    async with SessionLocal() as session:
        yield session


class ReserveIn(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=64)
    creator_id: str = Field(min_length=1, max_length=64)
    work_id: str = Field(min_length=1, max_length=64)
    currency: str = Field(min_length=3, max_length=8)
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=8)


class PayoutIn(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=64)
    creator_id: str = Field(min_length=1, max_length=64)
    work_id: str = Field(min_length=1, max_length=64)
    recipient_id: str = Field(min_length=1, max_length=64)
    currency: str = Field(min_length=3, max_length=8)
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=8)
    idempotency_key: str = Field(min_length=8, max_length=128)
    note: str = Field(default="work marketplace payout", max_length=128)


class ReleaseIn(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=64)
    creator_id: str = Field(min_length=1, max_length=64)
    work_id: str = Field(min_length=1, max_length=64)
    currency: str = Field(min_length=3, max_length=8)


async def _reservation(s: AsyncSession, tenant_id: str, creator_id: str, work_id: str, currency: str, lock: bool = False):
    q = select(Transaction).where(
        Transaction.tenant_id == tenant_id,
        Transaction.user_id == creator_id,
        Transaction.type == TxType.transfer,
        Transaction.reference == f"work-escrow:{work_id}",
    )
    if lock:
        q = q.with_for_update()
    return await s.scalar(q)


def _validate_existing_payout(existing: Transaction, body: PayoutIn, currency: str) -> None:
    meta = existing.meta or {}
    if (
        existing.currency != currency
        or abs(Decimal(str(existing.amount))) != body.amount
        or meta.get("to") != body.recipient_id
        or meta.get("work_id") != body.work_id
    ):
        raise HTTPException(409, "escrow payout idempotency key conflict")


@router.post("/reserve")
async def reserve_work_budget(body: ReserveIn, s: AsyncSession = Depends(db)):
    currency = body.currency.upper().strip()
    existing = await _reservation(s, body.tenant_id, body.creator_id, body.work_id, currency, lock=True)
    if existing:
        meta = existing.meta or {}
        if existing.currency != currency or Decimal(str(meta.get("reserved_amount", existing.amount))) != body.amount:
            raise HTTPException(409, "work escrow already exists with a different budget")
        if existing.status == TxStatus.cancelled:
            raise HTTPException(409, "work escrow was already released")
        return {"work_id": body.work_id, "status": "reserved", "reserved_amount": str(meta.get("reserved_amount", body.amount)), "remaining_amount": str(meta.get("remaining_amount", body.amount)), "duplicate": True}

    wallet = await s.scalar(select(Wallet).where(
        Wallet.tenant_id == body.tenant_id, Wallet.user_id == body.creator_id,
        Wallet.currency == currency,
    ).with_for_update())
    if not wallet:
        raise HTTPException(409, "creator wallet does not exist; add funds before publishing")
    # A concurrent retry may have reserved the budget while this request waited
    # for the wallet row lock. Re-read the journal before changing frozen funds.
    existing = await _reservation(s, body.tenant_id, body.creator_id, body.work_id, currency, lock=True)
    if existing:
        meta = existing.meta or {}
        if existing.currency != currency or Decimal(str(meta.get("reserved_amount", existing.amount))) != body.amount:
            raise HTTPException(409, "work escrow already exists with a different budget")
        if existing.status == TxStatus.cancelled:
            raise HTTPException(409, "work escrow was already released")
        await s.rollback()
        return {"work_id": body.work_id, "status": "reserved", "reserved_amount": str(meta.get("reserved_amount", body.amount)), "remaining_amount": str(meta.get("remaining_amount", body.amount)), "duplicate": True}
    available = Decimal(str(wallet.balance)) - Decimal(str(wallet.frozen))
    if available < body.amount:
        raise HTTPException(409, {"message": "insufficient available funds to publish this task", "required": str(body.amount), "available": str(max(available, Decimal('0'))), "currency": currency})
    wallet.frozen = Decimal(str(wallet.frozen)) + body.amount
    reservation = Transaction(
        tenant_id=body.tenant_id, user_id=body.creator_id, wallet_id=wallet.id,
        type=TxType.transfer, method=PaymentMethod.transfer,
        status=TxStatus.requires_approval, amount=body.amount, fee=0,
        currency=currency, reference=f"work-escrow:{body.work_id}",
        idempotency_key="work-escrow-reserve:" + hashlib.sha256(body.work_id.encode()).hexdigest(),
        meta={"source": "work-marketplace-escrow", "work_id": body.work_id,
              "creator_id": body.creator_id, "reserved_amount": str(body.amount),
              "remaining_amount": str(body.amount), "released_amount": "0"},
    )
    s.add(reservation)
    await s.commit()
    return {"work_id": body.work_id, "status": "reserved", "reserved_amount": str(body.amount), "remaining_amount": str(body.amount), "duplicate": False}


@router.post("/payout")
async def payout_from_work_escrow(body: PayoutIn, s: AsyncSession = Depends(db)):
    currency = body.currency.upper().strip()
    if body.creator_id == body.recipient_id:
        raise HTTPException(422, "escrow payout recipient cannot be the creator")
    reference = f"work-escrow-payout:{body.work_id}:{body.idempotency_key}"
    existing = await s.scalar(select(Transaction).where(
        Transaction.tenant_id == body.tenant_id, Transaction.user_id == body.creator_id,
        Transaction.type == TxType.transfer, Transaction.idempotency_key == body.idempotency_key,
        Transaction.status == TxStatus.completed,
    ))
    if existing:
        _validate_existing_payout(existing, body, currency)
        return {"transaction_id": str(existing.id), "status": "completed", "amount": str(body.amount), "currency": currency, "duplicate": True}

    reservation = await _reservation(s, body.tenant_id, body.creator_id, body.work_id, currency, lock=True)
    if not reservation or reservation.status != TxStatus.requires_approval:
        raise HTTPException(409, "funded work escrow not found or already released")
    meta = dict(reservation.meta or {})
    remaining = Decimal(str(meta.get("remaining_amount", 0)))
    if remaining < body.amount:
        raise HTTPException(409, {"message": "work escrow has insufficient remaining funds", "remaining": str(remaining), "requested": str(body.amount)})

    user_ids = sorted([body.creator_id, body.recipient_id])
    wallets = {}
    for uid in user_ids:
        await s.execute(insert(Wallet).values(
            tenant_id=body.tenant_id, user_id=uid, currency=currency,
            balance=0, frozen=0,
        ).on_conflict_do_nothing(index_elements=["tenant_id", "user_id", "currency"]))
    for uid in user_ids:
        wallets[uid] = await s.scalar(select(Wallet).where(
            Wallet.tenant_id == body.tenant_id, Wallet.user_id == uid, Wallet.currency == currency,
        ).with_for_update())
    source, destination = wallets[body.creator_id], wallets[body.recipient_id]
    if Decimal(str(source.frozen)) < body.amount or Decimal(str(source.balance)) < body.amount:
        raise HTTPException(409, "wallet escrow balance is inconsistent; payout blocked for safety")
    # Recheck the idempotency key after locks to make concurrent retries safe.
    existing = await s.scalar(select(Transaction).where(
        Transaction.tenant_id == body.tenant_id, Transaction.user_id == body.creator_id,
        Transaction.type == TxType.transfer, Transaction.idempotency_key == body.idempotency_key,
        Transaction.status == TxStatus.completed,
    ))
    if existing:
        _validate_existing_payout(existing, body, currency)
        await s.rollback()
        return {"transaction_id": str(existing.id), "status": "completed", "amount": str(body.amount), "currency": currency, "duplicate": True}

    source.balance = Decimal(str(source.balance)) - body.amount
    source.frozen = Decimal(str(source.frozen)) - body.amount
    destination.balance = Decimal(str(destination.balance)) + body.amount
    meta["remaining_amount"] = str((remaining - body.amount).quantize(Decimal("0.00000001")))
    meta["paid_amount"] = str((Decimal(str(meta.get("paid_amount", 0))) + body.amount).quantize(Decimal("0.00000001")))
    reservation.meta = meta
    if remaining - body.amount == 0:
        reservation.status = TxStatus.completed
        reservation.completed_at = datetime.utcnow()
    debit = Transaction(
        tenant_id=body.tenant_id, user_id=body.creator_id, wallet_id=source.id,
        type=TxType.transfer, method=PaymentMethod.transfer, status=TxStatus.completed,
        amount=-body.amount, fee=0, currency=currency, reference=reference,
        idempotency_key=body.idempotency_key, completed_at=datetime.utcnow(),
        meta={"source": "work-marketplace-escrow", "work_id": body.work_id, "to": body.recipient_id, "note": body.note},
    )
    credit = Transaction(
        tenant_id=body.tenant_id, user_id=body.recipient_id, wallet_id=destination.id,
        type=TxType.transfer, method=PaymentMethod.transfer, status=TxStatus.completed,
        amount=body.amount, fee=0, currency=currency, reference=reference,
        idempotency_key=body.idempotency_key, completed_at=datetime.utcnow(),
        meta={"source": "work-marketplace-escrow", "work_id": body.work_id, "from": body.creator_id, "note": body.note},
    )
    s.add_all([debit, credit])
    await s.commit()
    return {"transaction_id": str(debit.id), "status": "completed", "amount": str(body.amount), "currency": currency, "duplicate": False}


@router.post("/release-unused")
async def release_unused_work_budget(body: ReleaseIn, s: AsyncSession = Depends(db)):
    currency = body.currency.upper().strip()
    reservation = await _reservation(s, body.tenant_id, body.creator_id, body.work_id, currency, lock=True)
    if not reservation:
        return {"work_id": body.work_id, "status": "not_reserved", "released_amount": "0"}
    if reservation.status == TxStatus.cancelled:
        return {"work_id": body.work_id, "status": "released", "released_amount": str((reservation.meta or {}).get("released_amount", 0)), "duplicate": True}
    meta = dict(reservation.meta or {})
    remaining = Decimal(str(meta.get("remaining_amount", 0)))
    wallet = await s.scalar(select(Wallet).where(
        Wallet.tenant_id == body.tenant_id, Wallet.user_id == body.creator_id, Wallet.currency == currency,
    ).with_for_update())
    if not wallet or Decimal(str(wallet.frozen)) < remaining:
        raise HTTPException(409, "wallet escrow balance is inconsistent; release blocked for safety")
    wallet.frozen = Decimal(str(wallet.frozen)) - remaining
    meta["released_amount"] = str((Decimal(str(meta.get("released_amount", 0))) + remaining).quantize(Decimal("0.00000001")))
    meta["remaining_amount"] = "0"
    reservation.meta = meta
    reservation.status = TxStatus.cancelled
    await s.commit()
    return {"work_id": body.work_id, "status": "released", "released_amount": str(remaining), "duplicate": False}
