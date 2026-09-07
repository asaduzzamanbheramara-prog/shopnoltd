from datetime import datetime
from decimal import Decimal

from app.core.db import SessionLocal
from app.models.models import PaymentMethod, Transaction, TxStatus, Wallet
from app.providers.registry import get_provider
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import or_, select

router = APIRouter()


SUCCESS_STATUSES = {
    "COMPLETED",
    "SUCCESS",
    "PAID",
    "CAPTURED",
    "TRADE_SUCCESS",
}

FAILED_STATUSES = {
    "FAILED",
    "EXPIRED",
    "CANCELED",
    "CANCELLED",
}

TERMINAL_STATUSES = {
    TxStatus.completed,
    TxStatus.failed,
    TxStatus.cancelled,
}


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
        raise HTTPException(400, f"signature: {exc}") from exc

    async with SessionLocal() as s:
        data = event.get("data") or {}
        if not isinstance(data, dict):
            data = {}

        external = (
            event.get("external_id")
            or event.get("paymentID")
            or event.get("prepayId")
            or data.get("prepayId")
            or data.get("transaction_id")
            or data.get("payment_transaction_id")
        )
        order_reference = data.get("order_id") or event.get("order_id")
        if not external and not order_reference:
            return {"received": True, "warning": "missing transaction identity"}

        identity_filters = []
        if external:
            identity_filters.append(Transaction.external_id == str(external))
        if order_reference:
            identity_filters.append(Transaction.reference == str(order_reference))

        res = await s.execute(
            select(Transaction)
            .where(
                Transaction.method == method,
                or_(*identity_filters),
            )
            .with_for_update()
        )
        tx = res.scalar_one_or_none()

        if not tx:
            return {"received": True, "warning": "tx not found"}

        event_id = event.get("event_id") or headers.get("x-webhook-event-id")
        meta = dict(tx.meta or {})
        processed_events = list(meta.get("moneybag_webhook_event_ids", []))
        if event_id and event_id in processed_events:
            return {"received": True, "idempotent": True, "status": tx.status.value}

        if tx.status in TERMINAL_STATUSES:
            if event_id and event_id not in processed_events:
                processed_events.append(event_id)
                meta["moneybag_webhook_event_ids"] = processed_events[-20:]
                tx.meta = meta
                await s.commit()
            return {"received": True, "idempotent": True, "status": tx.status.value}

        status = (
            event.get("status")
            or data.get("status")
            or event.get("transactionStatus")
            or ""
        ).upper()

        # Moneybag's signed webhook is a reconciliation signal. For a success,
        # verify the authoritative transaction state from Moneybag before crediting.
        if method == PaymentMethod.moneybag and status in SUCCESS_STATUSES:
            verify_id = str(external or order_reference)
            try:
                verified = str(await p.get_status(verify_id)).upper()
            except Exception as exc:
                raise HTTPException(502, f"Moneybag verification failed: {exc}") from exc
            if verified not in SUCCESS_STATUSES:
                return {"received": True, "status": "pending", "verification": verified}

        event_amount = data.get("amount") or data.get("order_amount") or event.get("amount")
        if event_amount is not None:
            if Decimal(str(event_amount)) != Decimal(str(tx.amount)):
                raise HTTPException(400, "webhook amount does not match transaction")

        event_currency = data.get("currency") or event.get("currency")
        if event_currency and str(event_currency).upper() != str(tx.currency).upper():
            raise HTTPException(400, "webhook currency does not match transaction")

        if status in SUCCESS_STATUSES:
            tx.status = TxStatus.completed
            tx.completed_at = datetime.utcnow()
            wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update())
            w = wr.scalar_one()
            w.balance = Decimal(str(w.balance)) + Decimal(str(tx.amount)) - Decimal(str(tx.fee))
        elif status in FAILED_STATUSES:
            tx.status = TxStatus.cancelled if status in {"CANCELED", "CANCELLED"} else TxStatus.failed
            tx.completed_at = datetime.utcnow()
            if tx.type.value == "withdrawal":
                wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update())
                w = wr.scalar_one()
                w.frozen = Decimal(str(w.frozen)) - Decimal(str(tx.amount))
        else:
            return {"received": True, "status": "pending"}

        if event_id:
            processed_events.append(event_id)
            meta["moneybag_webhook_event_ids"] = processed_events[-20:]
            tx.meta = meta
        await s.commit()

    return {"received": True, "status": tx.status.value}
