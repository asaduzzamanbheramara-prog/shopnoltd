import json
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import config, fx
from app.database import Base, engine, get_db
from app.models import User, Wallet, Transaction, AuditLog
from app.gateways import get_gateway, REGISTRY, payoneer_payouts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("billing-engine")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Shopnoltd Billing Engine",
    description="Persistent multi-gateway payment platform (Stripe, PayPal, Razorpay, SSLCommerz, bKash, Nagad)",
    version="6.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def log_action(db: Session, action: str, user_id: Optional[str], details: dict):
    db.add(AuditLog(action=action, user_id=user_id, details=json.dumps(details)))
    db.commit()


def get_or_create_user(db: Session, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_or_create_wallet(db: Session, user_id: str, currency: str) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id, Wallet.currency == currency).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, currency=currency, balance=0.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


@app.get("/health")
def health():
    return {"status": "ok", "service": "billing-engine", "version": "6.0.0"}


@app.get("/gateways")
def list_gateways():
    """
    Honest status of every gateway: whether real credentials are configured
    (`live: true`) or it is currently running in demo mode (`live: false`).
    """
    out = []
    for name, gw in REGISTRY.items():
        out.append({
            "name": name,
            "live": gw.enabled,
            "currencies": {
                "stripe": ["USD", "EUR", "GBP", "AUD", "CAD", "SGD", "and more"],
                "paypal": ["USD", "EUR", "GBP", "AUD", "CAD"],
                "razorpay": ["INR", "USD"],
                "sslcommerz": ["BDT"],
                "bkash": ["BDT"],
                "nagad": ["BDT"],
                "crypto": ["BTC", "ETH", "USDT", "and ~200 more via NOWPayments"],
            }.get(name, []),
        })
    return {"gateways": out}


@app.get("/exchange-rates")
def exchange_rates():
    """Live FX rates when EXCHANGE_RATE_API_KEY is set, otherwise an honestly-labeled static snapshot."""
    data = fx.get_rates()
    return {
        "base": "USD",
        "live": data["live"],
        "fetched_at": data.get("fetched_at"),
        "rates": data["rates"],
        "note": data.get("note"),
    }


@app.get("/exchange-rates/convert")
def exchange_convert(amount: float, from_currency: str, to_currency: str):
    try:
        converted, rate = fx.convert_currency(amount, from_currency.upper(), to_currency.upper())
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"amount": amount, "from": from_currency.upper(), "to": to_currency.upper(),
            "converted": converted, "rate": rate, "live": fx.get_rates()["live"]}


class PayoneerPayoutRequest(BaseModel):
    payee_id: str
    amount: float
    currency: str
    description: str = "Shopnoltd payout"


@app.post("/payouts/payoneer")
def send_payoneer_payout(req: PayoneerPayoutRequest):
    """
    Pays a seller/affiliate/supplier via Payoneer. This is NOT a customer
    checkout option -- Payoneer has no public API for customers to pay a
    merchant directly, only for merchants/marketplaces to pay recipients out.
    """
    return payoneer_payouts.send_payout(req.payee_id, req.amount, req.currency, req.description)


class CheckoutRequest(BaseModel):
    gateway: str
    amount: float
    currency: str
    customer_email: str
    reference: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None


@app.post("/checkout")
def create_checkout(req: CheckoutRequest, db: Session = Depends(get_db)):
    try:
        gw = get_gateway(req.gateway)
    except KeyError as e:
        raise HTTPException(400, str(e))

    user = get_or_create_user(db, req.customer_email)
    reference = req.reference or f"ord_{user.id}_{int(__import__('time').time())}"

    try:
        result = gw.create_payment(
            amount=req.amount, currency=req.currency, reference=reference,
            customer_email=req.customer_email, customer_name=req.customer_name,
            customer_phone=req.customer_phone,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Gateway %s create_payment failed", req.gateway)
        raise HTTPException(502, f"{req.gateway} error: {e}")

    txn = Transaction(
        user_id=user.id, gateway=req.gateway, gateway_reference=result.get("gateway_reference"),
        amount=req.amount, currency=req.currency.upper(), status=result.get("status", "pending"),
        is_demo=result.get("is_demo", False), raw_response=json.dumps(result),
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    log_action(db, "checkout_created", user.id, {"gateway": req.gateway, "txn_id": txn.id})

    return {
        "transaction_id": txn.id,
        "gateway": req.gateway,
        "is_demo": result.get("is_demo", False),
        "status": txn.status,
        "redirect_url": result.get("redirect_url"),
        "gateway_reference": result.get("gateway_reference"),
        "note": result.get("note"),
    }


def _complete_transaction(db: Session, gateway_reference: str, gateway: str, status: str, amount: Optional[float] = None):
    txn = db.query(Transaction).filter(
        Transaction.gateway_reference == gateway_reference, Transaction.gateway == gateway
    ).first()
    if not txn:
        logger.warning("Webhook for unknown transaction: %s/%s", gateway, gateway_reference)
        return None
    txn.status = status
    db.commit()
    if status == "completed":
        wallet = get_or_create_wallet(db, txn.user_id, txn.currency)
        wallet.balance += amount if amount is not None else txn.amount
        db.commit()
    log_action(db, "webhook_processed", txn.user_id, {"gateway": gateway, "status": status})
    return txn


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    gw = get_gateway("stripe")
    payload = await request.body()
    try:
        event = gw.verify_webhook(payload, dict(request.headers))
    except Exception as e:
        raise HTTPException(400, f"Webhook verification failed: {e}")
    _complete_transaction(db, event["gateway_reference"], "stripe", event["status"], event.get("amount"))
    return {"received": True}


@app.post("/webhook/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    gw = get_gateway("razorpay")
    payload = await request.body()
    try:
        event = gw.verify_webhook(payload, dict(request.headers))
    except Exception as e:
        raise HTTPException(400, f"Webhook verification failed: {e}")
    _complete_transaction(db, event["gateway_reference"], "razorpay", event["status"], event.get("amount"))
    return {"received": True}


@app.get("/webhook/sslcommerz/success")
def sslcommerz_success(val_id: str, tran_id: str, db: Session = Depends(get_db)):
    gw = get_gateway("sslcommerz")
    data = gw.validate_transaction(val_id)
    status = "completed" if data.get("status") in ("VALID", "VALIDATED") else "failed"
    _complete_transaction(db, tran_id, "sslcommerz", status, float(data.get("amount", 0)) or None)
    return {"received": True, "status": status}


@app.get("/webhook/sslcommerz/fail")
@app.get("/webhook/sslcommerz/cancel")
def sslcommerz_fail_cancel(tran_id: str, db: Session = Depends(get_db)):
    _complete_transaction(db, tran_id, "sslcommerz", "failed")
    return {"received": True, "status": "failed"}


@app.get("/webhook/bkash/callback")
def bkash_callback(paymentID: str, status: str, db: Session = Depends(get_db)):
    if status != "success":
        _complete_transaction(db, paymentID, "bkash", "failed")
        return {"received": True, "status": "failed"}
    gw = get_gateway("bkash")
    data = gw.execute_payment(paymentID)
    ok = data.get("transactionStatus") == "Completed"
    _complete_transaction(db, paymentID, "bkash", "completed" if ok else "failed", float(data.get("amount", 0)) or None)
    return {"received": True, "status": "completed" if ok else "failed"}


@app.get("/webhook/nagad/callback")
def nagad_callback(payment_ref_id: str, status: str, db: Session = Depends(get_db)):
    ok = status.lower() == "success"
    _complete_transaction(db, payment_ref_id, "nagad", "completed" if ok else "failed")
    return {"received": True, "status": "completed" if ok else "failed"}


@app.post("/webhook/crypto")
async def crypto_webhook(request: Request, db: Session = Depends(get_db)):
    gw = get_gateway("crypto")
    payload = await request.body()
    try:
        event = gw.verify_webhook(payload, dict(request.headers))
    except Exception as e:
        raise HTTPException(400, f"Webhook verification failed: {e}")
    _complete_transaction(db, event["gateway_reference"], "crypto", event["status"], event.get("amount"))
    return {"received": True}


@app.get("/wallet/{email}")
def get_wallet(email: str, currency: str = "BDT", db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")
    wallet = get_or_create_wallet(db, user.id, currency)
    return {"user_id": user.id, "currency": wallet.currency, "balance": wallet.balance}


@app.get("/transactions/{email}")
def get_transactions(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")
    txns = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.created_at.desc()).all()
    return [
        {
            "id": t.id, "gateway": t.gateway, "amount": t.amount, "currency": t.currency,
            "status": t.status, "is_demo": t.is_demo, "created_at": t.created_at.isoformat(),
        }
        for t in txns
    ]
