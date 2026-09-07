from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.gateways import get_gateway
from app.ledger import apply_ledger_entry
from app.models import Transaction

router = APIRouter()


def _verify_and_complete(db: Session, order_id: str, transaction_id: str):
    txn = (
        db.query(Transaction)
        .filter(Transaction.gateway == "moneybag", Transaction.gateway_reference == order_id)
        .first()
    )
    if not txn:
        raise HTTPException(404, "Moneybag order not found")

    gw = get_gateway("moneybag")
    try:
        response = gw.verify_transaction(transaction_id)
    except Exception as exc:
        raise HTTPException(502, f"Moneybag verification failed: {exc}") from exc

    data = response.get("data") or {}
    verified = bool(data.get("verified"))
    status = str(data.get("status") or "").upper()
    verified_order_id = str(data.get("order_id") or "")
    verified_currency = str(data.get("currency") or "").upper()

    try:
        verified_amount = float(data.get("amount"))
    except (TypeError, ValueError):
        verified_amount = None

    if not verified or status not in {"SUCCESS", "COMPLETED", "PAID", "VALID", "VALIDATED"}:
        return {"received": True, "status": "pending", "verified": False}
    if verified_order_id != order_id:
        raise HTTPException(400, "Moneybag order reference mismatch")
    if verified_currency != txn.currency:
        raise HTTPException(400, "Moneybag currency mismatch")
    if verified_amount is None or abs(verified_amount - txn.amount) > 0.000001:
        raise HTTPException(400, "Moneybag amount mismatch")

    # Idempotency: a repeated redirect/webhook must never credit the wallet twice.
    if txn.status == "completed":
        return {
            "received": True,
            "status": "completed",
            "verified": True,
            "transaction_id": transaction_id,
            "already_completed": True,
        }

    txn.status = "completed"
    txn.raw_response = response.__class__.__name__ and __import__("json").dumps(response)
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
    db.commit()
    return {
        "received": True,
        "status": "completed",
        "verified": True,
        "transaction_id": transaction_id,
        "already_completed": False,
    }


@router.get("/webhook/moneybag/success")
def moneybag_success(
    order_id: str = Query(...),
    transaction_id: str = Query(...),
    db: Session = Depends(get_db),
):
    return _verify_and_complete(db, order_id, transaction_id)


@router.get("/webhook/moneybag/fail")
def moneybag_fail(order_id: str = Query(...), db: Session = Depends(get_db)):
    txn = (
        db.query(Transaction)
        .filter(Transaction.gateway == "moneybag", Transaction.gateway_reference == order_id)
        .first()
    )
    if not txn:
        raise HTTPException(404, "Moneybag order not found")
    if txn.status != "completed":
        txn.status = "failed"
        db.commit()
    return {"received": True, "status": "failed"}


@router.get("/webhook/moneybag/cancel")
def moneybag_cancel(order_id: str = Query(...), db: Session = Depends(get_db)):
    txn = (
        db.query(Transaction)
        .filter(Transaction.gateway == "moneybag", Transaction.gateway_reference == order_id)
        .first()
    )
    if not txn:
        raise HTTPException(404, "Moneybag order not found")
    if txn.status != "completed":
        txn.status = "cancelled"
        db.commit()
    return {"received": True, "status": "cancelled"}
