import hashlib
import hmac
import json
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.gateways import get_gateway
from app.ledger import apply_ledger_entry
from app.models import MoneybagWebhookEvent, Transaction

router = APIRouter()

_SUCCESS_STATUSES = {"SUCCESS", "COMPLETED", "PAID", "VALID", "VALIDATED"}


def _find_transaction(db: Session, order_id: str) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(
            Transaction.gateway == "moneybag",
            Transaction.gateway_reference == order_id,
        )
        .with_for_update()
        .first()
    )


def _record_webhook_event(
    db: Session,
    *,
    event_id: str,
    event_type: str,
    transaction_id: str,
    order_id: str,
    raw_body: bytes,
) -> MoneybagWebhookEvent | None:
    """Persist event identity before any webhook side effect.

    The unique event_id is the durable idempotency key. A duplicate delivery
    is acknowledged without re-running the payment side effect. A different
    payload using an existing event_id is rejected rather than silently
    accepting a potentially corrupted/replayed event.
    """
    payload_sha256 = hashlib.sha256(raw_body).hexdigest()
    event = MoneybagWebhookEvent(
        event_id=event_id,
        event_type=event_type,
        transaction_id=transaction_id or None,
        order_id=order_id or None,
        payload_sha256=payload_sha256,
        status="received",
    )
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(MoneybagWebhookEvent)
            .filter(MoneybagWebhookEvent.event_id == event_id)
            .first()
        )
        if not existing:
            raise HTTPException(status_code=409, detail="Moneybag webhook event conflict")
        if existing.payload_sha256 != payload_sha256:
            raise HTTPException(status_code=409, detail="Moneybag webhook event payload mismatch")
        return None
    return event


def _verify_and_complete(
    db: Session,
    transaction_id: str,
    expected_order_id: str | None = None,
):
    gw = get_gateway("moneybag")
    try:
        response = gw.verify_transaction(transaction_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Moneybag verification failed") from exc

    data = response.get("data") or {}
    verified = bool(data.get("verified"))
    status = str(data.get("status") or "").upper()
    verified_order_id = str(data.get("order_id") or "")
    verified_currency = str(data.get("currency") or "").upper()
    verified_transaction_id = str(data.get("transaction_id") or transaction_id)

    try:
        verified_amount = float(data.get("amount"))
    except (TypeError, ValueError):
        verified_amount = None

    if expected_order_id and verified_order_id != expected_order_id:
        raise HTTPException(status_code=400, detail="Moneybag order reference mismatch")

    txn = _find_transaction(db, verified_order_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Moneybag order not found")

    if not verified or status not in _SUCCESS_STATUSES:
        return {
            "received": True,
            "status": "pending",
            "verified": False,
            "transaction_id": verified_transaction_id,
        }

    if verified_currency != str(txn.currency).upper():
        raise HTTPException(status_code=400, detail="Moneybag currency mismatch")
    if verified_amount is None or abs(verified_amount - float(txn.amount)) > 0.000001:
        raise HTTPException(status_code=400, detail="Moneybag amount mismatch")

    # The transaction row is locked above. A repeated redirect/webhook waits
    # for the first request, then observes completed and cannot credit twice.
    if txn.status == "completed":
        return {
            "received": True,
            "status": "completed",
            "verified": True,
            "transaction_id": verified_transaction_id,
            "already_completed": True,
        }

    txn.status = "completed"
    txn.raw_response = json.dumps(response)
    db.flush()
    apply_ledger_entry(
        db,
        txn.user_id,
        txn.currency,
        delta=verified_amount,
        entry_type="deposit",
        reason="Payment completed via moneybag",
        reference=txn.id,
        allow_negative=True,
    )
    return {
        "received": True,
        "status": "completed",
        "verified": True,
        "transaction_id": verified_transaction_id,
        "already_completed": False,
    }


def _verify_webhook_signature(raw_body: bytes, signature: str, timestamp: str) -> None:
    if not config.MONEYBAG_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Moneybag webhook secret is not configured")
    try:
        timestamp_int = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid Moneybag webhook timestamp") from exc

    if abs(int(time.time()) - timestamp_int) > 300:
        raise HTTPException(status_code=401, detail="Expired Moneybag webhook")

    signed_payload = timestamp.encode("utf-8") + b"." + raw_body
    expected = "sha256=" + hmac.new(
        config.MONEYBAG_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid Moneybag webhook signature")


@router.get("/webhook/moneybag/success")
def moneybag_success(
    transaction_id: str = Query(...),
    order_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return _verify_and_complete(db, transaction_id, order_id)


@router.get("/webhook/moneybag/fail")
def moneybag_fail(
    order_id: str | None = Query(default=None),
    transaction_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if not order_id:
        if not transaction_id:
            raise HTTPException(status_code=400, detail="order_id or transaction_id is required")
        gw = get_gateway("moneybag")
        try:
            response = gw.verify_transaction(transaction_id)
            order_id = str((response.get("data") or {}).get("order_id") or "")
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Moneybag verification failed") from exc
    txn = _find_transaction(db, order_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Moneybag order not found")
    if txn.status != "completed":
        txn.status = "failed"
        db.commit()
    return {"received": True, "status": "failed"}


@router.get("/webhook/moneybag/cancel")
def moneybag_cancel(
    order_id: str | None = Query(default=None),
    transaction_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if not order_id:
        if not transaction_id:
            raise HTTPException(status_code=400, detail="order_id or transaction_id is required")
        gw = get_gateway("moneybag")
        try:
            response = gw.verify_transaction(transaction_id)
            order_id = str((response.get("data") or {}).get("order_id") or "")
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Moneybag verification failed") from exc
    txn = _find_transaction(db, order_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Moneybag order not found")
    if txn.status != "completed":
        txn.status = "cancelled"
        db.commit()
    return {"received": True, "status": "cancelled"}


@router.post("/webhook/moneybag/ipn")
async def moneybag_ipn(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("X-Webhook-Signature", "")
    timestamp = request.headers.get("X-Webhook-Timestamp", "")
    event_id = request.headers.get("X-Webhook-Event-Id")
    event_type = request.headers.get("X-Webhook-Event-Type", "")

    if not event_id or not event_type:
        raise HTTPException(status_code=400, detail="Missing Moneybag webhook headers")
    _verify_webhook_signature(raw_body, signature, timestamp)

    try:
        event = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid Moneybag webhook JSON") from exc

    data = event.get("data") or {}
    transaction_id = str(data.get("transaction_id") or "")
    order_id = str(data.get("order_id") or data.get("reference") or "")

    persisted_event = _record_webhook_event(
        db,
        event_id=event_id,
        event_type=event_type,
        transaction_id=transaction_id,
        order_id=order_id,
        raw_body=raw_body,
    )
    if persisted_event is None:
        return {"received": True, "event_id": event_id, "duplicate": True}

    if not transaction_id or not order_id:
        persisted_event.status = "ignored"
        persisted_event.processed_at = datetime.utcnow()
        db.commit()
        return {"received": True, "event_id": event_id, "ignored": True}

    if event_type == "payment.success":
        result = _verify_and_complete(db, transaction_id, order_id)
        persisted_event.status = "processed" if result.get("verified") else "pending"
        persisted_event.processed_at = datetime.utcnow()
        db.commit()
        result["event_id"] = event_id
        return result

    txn = _find_transaction(db, order_id)
    if txn and txn.status != "completed":
        if event_type == "payment.failed":
            txn.status = "failed"
        elif event_type == "payment.cancelled":
            txn.status = "cancelled"
    persisted_event.status = "processed"
    persisted_event.processed_at = datetime.utcnow()
    db.commit()

    return {"received": True, "event_id": event_id, "status": "acknowledged"}
