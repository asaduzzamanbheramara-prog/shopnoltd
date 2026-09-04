from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.core.db import SessionLocal
from app.models.models import PaymentMethod, Transaction, TxStatus, TxType, Wallet
from app.providers.registry import get_provider
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

router = APIRouter()

SUCCESS_STATUSES = {"COMPLETED", "SUCCESS", "PAID", "CAPTURED", "TRADE_SUCCESS"}
FAILED_STATUSES = {"FAILED", "EXPIRED", "CANCELED", "CANCELLED"}
TERMINAL_STATUSES = {TxStatus.completed, TxStatus.failed, TxStatus.cancelled}


def _event_value(event: dict, *keys):
    for key in keys:
        value = event.get(key)
        if value is not None:
            return value
        nested = event.get("data")
        if isinstance(nested, dict) and nested.get(key) is not None:
            return nested[key]
    return None


def _validate_amount_currency(tx, event):
    raw_amount = _event_value(event, "amount", "total_amount", "totalAmount", "paid_amount", "paidAmount")
    if raw_amount is not None:
        try:
            if Decimal(str(raw_amount)) != Decimal(str(tx.amount)):
                raise HTTPException(400, "webhook amount mismatch")
        except InvalidOperation as exc:
            raise HTTPException(400, "invalid webhook amount") from exc
    event_currency = _event_value(event, "currency", "currencyCode")
    if event_currency and str(event_currency).upper() != str(tx.currency).upper():
        raise HTTPException(400, "webhook currency mismatch")


@router.post("/{provider}")
async def webhook(provider: str, request: Request):
    body = await request.body()
    headers = dict(request.headers)
    try:
        method = PaymentMethod(provider)
    except ValueError as exc:
        raise HTTPException(400, "unknown provider") from exc
    p = get_provider(method)
    try:
        event = await p.verify_webhook(body, headers)
    except Exception as exc:
        raise HTTPException(400, f"signature verification failed: {exc}") from exc
    if not isinstance(event, dict):
        raise HTTPException(400, "invalid webhook payload")

    async with SessionLocal() as s:
        external = _event_value(event, "external_id", "paymentID", "prepayId", "transaction_id", "transactionId")
        if not external:
            return {"received": True}
        res = await s.execute(
            select(Transaction)
            .where(Transaction.external_id == str(external), Transaction.method == method)
            .with_for_update()
        )
        tx = res.scalar_one_or_none()
        if tx and tx.status in TERMINAL_STATUSES:
            return {"received": True, "idempotent": True, "status": tx.status.value}
        if not tx:
            return {"received": True, "warning": "tx not found"}

        status = str(_event_value(event, "status", "transactionStatus") or "").upper()
        if status in SUCCESS_STATUSES:
            _validate_amount_currency(tx, event)
            wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update())
            w = wr.scalar_one_or_none()
            if not w:
                raise HTTPException(500, "wallet not found")
            amount = Decimal(str(tx.amount))
            fee = Decimal(str(tx.fee))
            if tx.type == TxType.deposit or tx.type == TxType.refund:
                w.balance = Decimal(str(w.balance)) + amount - fee
            elif tx.type == TxType.withdrawal:
                w.balance = Decimal(str(w.balance)) - amount - fee
                w.frozen = max(Decimal("0"), Decimal(str(w.frozen)) - amount)
            elif tx.type in {TxType.transfer, TxType.exchange, TxType.subscription, TxType.fee}:
                raise HTTPException(400, "webhook settlement is not supported for this transaction type")
            tx.status = TxStatus.completed
            tx.completed_at = datetime.utcnow()
        elif status in FAILED_STATUSES:
            if tx.type == TxType.withdrawal:
                wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update())
                w = wr.scalar_one_or_none()
                if w:
                    w.frozen = max(Decimal("0"), Decimal(str(w.frozen)) - Decimal(str(tx.amount)))
            tx.status = TxStatus.failed
            tx.completed_at = datetime.utcnow()
        else:
            return {"received": True, "status": "ignored"}
        await s.commit()
    return {"received": True}
