"""Payment-provider callbacks.

Provider callbacks are treated as untrusted input. A wallet is credited only
when the provider-side transaction is found, the amount/currency/order identity
match the Shopnoltd transaction, and the provider API confirms success.
"""

import hashlib
from datetime import datetime
from decimal import Decimal

from app.core.db import SessionLocal
from app.models.models import PaymentMethod, Transaction, TxStatus, TxType, Wallet, WebhookEvent
from app.providers.registry import get_provider
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

router = APIRouter()

SUCCESS_STATUSES = {
    "COMPLETED",
    "SUCCESS",
    "SUCCESSFUL",
    "PAID",
    "CAPTURED",
    "TRADE_SUCCESS",
}
FAILED_STATUSES = {"FAILED", "EXPIRED", "CANCELED", "CANCELLED"}
TERMINAL_STATUSES = {TxStatus.completed, TxStatus.failed, TxStatus.cancelled}
VERIFIED_CALLBACK_METHODS = {PaymentMethod.bkash, PaymentMethod.nagad}


def _status(event: dict) -> str:
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    return str(
        event.get("status")
        or event.get("transactionStatus")
        or data.get("status")
        or data.get("transactionStatus")
        or ""
    ).upper()


def _amount(event: dict):
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    return data.get("amount") or data.get("order_amount") or event.get("amount")


def _currency(event: dict):
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    return data.get("currency") or event.get("currency")


def _order_id(event: dict):
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    return (
        event.get("merchantInvoiceNumber")
        or event.get("merchantInvoiceNo")
        or event.get("orderId")
        or event.get("order_id")
        or data.get("merchantInvoiceNumber")
        or data.get("orderId")
        or data.get("order_id")
    )


async def _apply_event(method: PaymentMethod, event: dict, body: bytes, headers: dict):
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    external = (
        event.get("external_id")
        or event.get("paymentID")
        or event.get("paymentId")
        or event.get("paymentReferenceId")
        or event.get("payment_ref_id")
        or event.get("prepayId")
        or data.get("paymentID")
        or data.get("paymentReferenceId")
        or data.get("payment_ref_id")
        or data.get("prepayId")
        or data.get("transaction_id")
        or data.get("payment_transaction_id")
    )
    order_reference = _order_id(event)
    if not external and not order_reference:
        raise HTTPException(400, "provider callback is missing transaction identity")

    async with SessionLocal() as s:
        identity_filters = []
        if external:
            identity_filters.append(Transaction.external_id == str(external))
        if order_reference:
            identity_filters.extend(
                [
                    Transaction.reference == str(order_reference),
                    Transaction.id == str(order_reference),
                ]
            )

        tx = await s.scalar(
            select(Transaction)
            .where(Transaction.method == method, or_(*identity_filters))
            .with_for_update()
        )
        if not tx:
            return {"received": True, "warning": "tx not found"}

        if external and tx.external_id and str(tx.external_id) != str(external):
            raise HTTPException(400, "provider transaction identity does not match")
        if order_reference and str(order_reference) != str(tx.id) and str(order_reference) != str(tx.reference or ""):
            raise HTTPException(400, "provider order identity does not match")

        supplied_event_id = event.get("event_id") or headers.get("x-webhook-event-id")
        if supplied_event_id:
            supplied_event_id = str(supplied_event_id)
            event_key = (
                supplied_event_id
                if len(supplied_event_id) <= 128
                else hashlib.sha256(supplied_event_id.encode()).hexdigest()
            )
        else:
            event_key = hashlib.sha256(body).hexdigest()

        webhook_event = WebhookEvent(
            provider=method.value,
            event_key=event_key,
            transaction_id=tx.id,
            payload_hash=hashlib.sha256(body).hexdigest(),
            status="received",
        )
        s.add(webhook_event)
        try:
            await s.flush()
        except IntegrityError:
            await s.rollback()
            return {"received": True, "idempotent": True}

        if tx.status in TERMINAL_STATUSES:
            webhook_event.status = "ignored_terminal"
            webhook_event.processed_at = datetime.utcnow()
            await s.commit()
            return {"received": True, "idempotent": True, "status": tx.status.value}

        status = _status(event)
        event_amount = _amount(event)
        if event_amount is not None and Decimal(str(event_amount)) != Decimal(str(tx.amount)):
            raise HTTPException(400, "provider amount does not match transaction")

        event_currency = _currency(event)
        if event_currency and str(event_currency).upper() != str(tx.currency).upper():
            raise HTTPException(400, "provider currency does not match transaction")

        if status in SUCCESS_STATUSES:
            tx.status = TxStatus.completed
            tx.completed_at = datetime.utcnow()
            wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update())
            wallet = wr.scalar_one()
            wallet.balance = Decimal(str(wallet.balance)) + Decimal(str(tx.amount)) - Decimal(str(tx.fee))
        elif status in FAILED_STATUSES:
            tx.status = TxStatus.cancelled if status in {"CANCELED", "CANCELLED"} else TxStatus.failed
            tx.completed_at = datetime.utcnow()
            if tx.type == TxType.withdrawal:
                wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update())
                wallet = wr.scalar_one()
                wallet.frozen = Decimal(str(wallet.frozen)) - Decimal(str(tx.amount))
        else:
            webhook_event.status = "pending"
            await s.commit()
            return {"received": True, "status": "pending"}

        webhook_event.status = "processed"
        webhook_event.processed_at = datetime.utcnow()
        await s.commit()
        return {"received": True, "status": tx.status.value}


async def _verified_mfs_event(method: PaymentMethod, request: Request, query: dict | None = None):
    p = get_provider(method)
    params = query or {}
    payment_id = (
        params.get("paymentID")
        or params.get("paymentId")
        or params.get("paymentReferenceId")
        or params.get("payment_ref_id")
    )
    if not payment_id:
        raise HTTPException(400, f"{method.value} callback is missing payment identifier")

    try:
        event = await p.confirm_callback(str(payment_id))
    except Exception as exc:
        raise HTTPException(502, f"{method.value} provider verification failed") from exc

    return await _apply_event(method, event, await request.body(), dict(request.headers))


@router.api_route("/bkash", methods=["GET", "POST"])
async def bkash_callback(request: Request):
    if request.method == "GET":
        return await _verified_mfs_event(PaymentMethod.bkash, request, dict(request.query_params))
    body = await request.body()
    p = get_provider(PaymentMethod.bkash)
    try:
        event = await p.verify_webhook(body, dict(request.headers))
    except Exception as exc:
        raise HTTPException(400, "bKash verification failed") from exc
    return await _apply_event(PaymentMethod.bkash, event, body, dict(request.headers))


@router.api_route("/nagad", methods=["GET", "POST"])
async def nagad_callback(request: Request):
    if request.method == "GET":
        return await _verified_mfs_event(PaymentMethod.nagad, request, dict(request.query_params))
    body = await request.body()
    p = get_provider(PaymentMethod.nagad)
    try:
        event = await p.verify_webhook(body, dict(request.headers))
    except Exception as exc:
        raise HTTPException(400, "Nagad verification failed") from exc
    return await _apply_event(PaymentMethod.nagad, event, body, dict(request.headers))


@router.post("/{provider}")
async def webhook(provider: str, request: Request):
    body = await request.body()
    headers = dict(request.headers)
    try:
        method = PaymentMethod(provider)
    except ValueError as exc:
        raise HTTPException(400, "unknown provider") from exc

    if method in VERIFIED_CALLBACK_METHODS:
        raise HTTPException(405, "use the provider callback endpoint")

    p = get_provider(method)
    try:
        event = await p.verify_webhook(body, headers)
    except Exception as exc:
        raise HTTPException(400, f"signature: {exc}") from exc
    return await _apply_event(method, event, body, headers)
