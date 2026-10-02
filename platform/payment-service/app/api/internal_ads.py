"""Privileged, idempotent wallet operations for the advertising network."""

from decimal import Decimal

from app.core.db import SessionLocal
from app.core.security import require_internal_key
from app.models.models import PaymentMethod, Transaction, TxStatus, TxType, Wallet
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(dependencies=[Depends(require_internal_key)])


async def db():
    async with SessionLocal() as s:
        yield s


class AdWalletOperation(BaseModel):
    tenant_id: str = Field(default="default", min_length=1, max_length=64)
    user_id: str = Field(min_length=1, max_length=64)
    currency: str = Field(min_length=3, max_length=8)
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=8)
    operation: str = Field(pattern="^(debit|credit)$")
    idempotency_key: str = Field(min_length=8, max_length=128)
    reference: str = Field(min_length=1, max_length=128)


@router.post("/wallet-operation")
async def ad_wallet_operation(body: AdWalletOperation, s: AsyncSession = Depends(db)):
    currency = body.currency.upper()

    existing = await s.scalar(
        select(Transaction).where(
            Transaction.tenant_id == body.tenant_id,
            Transaction.user_id == body.user_id,
            Transaction.idempotency_key == body.idempotency_key,
        )
    )
    if existing:
        if existing.type not in {TxType.deposit, TxType.withdrawal} or existing.currency != currency:
            raise HTTPException(409, "idempotency key already belongs to a different operation")
        return {
            "transaction_id": str(existing.id),
            "status": existing.status.value,
            "amount": str(existing.amount),
            "currency": existing.currency,
            "operation": "credit" if existing.type == TxType.deposit else "debit",
            "reference": existing.reference,
        }

    wallet = await s.scalar(
        select(Wallet)
        .where(
            Wallet.tenant_id == body.tenant_id,
            Wallet.user_id == body.user_id,
            Wallet.currency == currency,
        )
        .with_for_update()
    )
    if wallet is None:
        wallet = Wallet(
            tenant_id=body.tenant_id,
            user_id=body.user_id,
            currency=currency,
            balance=Decimal("0"),
            frozen=Decimal("0"),
        )
        s.add(wallet)
        try:
            await s.flush()
        except IntegrityError:
            await s.rollback()
            wallet = await s.scalar(
                select(Wallet)
                .where(
                    Wallet.tenant_id == body.tenant_id,
                    Wallet.user_id == body.user_id,
                    Wallet.currency == currency,
                )
                .with_for_update()
            )
            if wallet is None:
                raise HTTPException(409, "wallet creation conflict")
    
    if body.operation == "debit":
        available = Decimal(wallet.balance) - Decimal(wallet.frozen or 0)
        if available < body.amount:
            raise HTTPException(409, "insufficient available wallet balance")
        wallet.balance = Decimal(wallet.balance) - body.amount
        tx_type = TxType.withdrawal
    else:
        wallet.balance = Decimal(wallet.balance) + body.amount
        tx_type = TxType.deposit

    tx = Transaction(
        tenant_id=body.tenant_id,
        user_id=body.user_id,
        wallet_id=wallet.id,
        type=tx_type,
        method=PaymentMethod.transfer,
        status=TxStatus.completed,
        amount=body.amount,
        fee=Decimal("0"),
        currency=currency,
        reference=body.reference,
        idempotency_key=body.idempotency_key,
        meta={"source": "ad-network", "reference": body.reference},
    )
    s.add(tx)
    try:
        await s.commit()
    except IntegrityError:
        await s.rollback()
        existing = await s.scalar(
            select(Transaction).where(
                Transaction.tenant_id == body.tenant_id,
                Transaction.user_id == body.user_id,
                Transaction.idempotency_key == body.idempotency_key,
            )
        )
        if existing:
            return {
                "transaction_id": str(existing.id),
                "status": existing.status.value,
                "amount": str(existing.amount),
                "currency": existing.currency,
                "operation": "credit" if existing.type == TxType.deposit else "debit",
                "reference": existing.reference,
            }
        raise HTTPException(409, "idempotency conflict")
    return {
        "transaction_id": str(tx.id),
        "status": tx.status.value,
        "amount": str(tx.amount),
        "currency": currency,
        "operation": body.operation,
        "reference": body.reference,
    }
