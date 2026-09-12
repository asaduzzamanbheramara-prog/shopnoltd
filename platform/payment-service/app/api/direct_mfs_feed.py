"""Signed Android/SMS relay ingestion for direct bKash/Nagad/Rocket payments.

The relay never receives a customer's PIN/OTP. It only forwards a locally
received transaction notification after the receiving phone has authorized
the relay request. The server credits a wallet only when the signed event
matches exactly one active payment intent, the configured receiving account,
the requested amount/currency, and a previously unused provider TxID.

This is intentionally an adapter/feed boundary: the Android relay remains a
separate device-side component and must use the same canonical JSON bytes and
HMAC secret configured for this service.
"""

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.models import (
    DirectPaymentAccount,
    DirectPaymentIntent,
    DirectPaymentSubmission,
    PaymentMethod,
    Transaction,
    TxStatus,
    TxType,
    Wallet,
)
from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
PROVIDERS = {"bkash", "nagad", "rocket"}


def _canonical_json(body: bytes) -> bytes:
    try:
        obj = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(400, "invalid JSON feed payload") from exc
    return json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")


def _verify_signature(body: bytes, timestamp: str, signature: str) -> None:
    if not settings.direct_payment_feed_enabled:
        raise HTTPException(503, "direct MFS feed is disabled")
    secret = settings.direct_payment_feed_secret.strip()
    if not secret:
        raise HTTPException(503, "direct MFS feed secret is not configured")
    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise HTTPException(401, "invalid feed timestamp") from exc
    if abs(int(time.time()) - ts) > settings.direct_payment_feed_max_skew_seconds:
        raise HTTPException(401, "stale feed timestamp")

    canonical = _canonical_json(body)
    message = timestamp.encode("utf-8") + b"." + canonical
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    supplied = signature.removeprefix("sha256=").strip().lower()
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(401, "invalid feed signature")


def _norm_number(value: str) -> str:
    value = "".join(ch for ch in str(value).strip() if ch.isdigit() or ch == "+")
    if value.startswith("+880"):
        return "0" + value[4:]
    if value.startswith("880") and len(value) >= 13:
        return "0" + value[3:]
    return value


def _decimal(value, field: str) -> Decimal:
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HTTPException(422, f"invalid {field}") from exc
    if out <= 0:
        raise HTTPException(422, f"{field} must be positive")
    return out


async def _credit_verified_feed(
    s: AsyncSession,
    *,
    provider: str,
    txid: str,
    amount: Decimal,
    receiver_number: str,
    sender_number: str | None,
    reference: str | None,
    occurred_at: str | None,
    raw_message: str | None,
    balance: str | None,
    source_device: str | None,
):
    method = PaymentMethod(provider)

    duplicate = await s.scalar(
        select(DirectPaymentSubmission)
        .where(
            DirectPaymentSubmission.provider == provider,
            DirectPaymentSubmission.txid == txid,
        )
        .with_for_update()
    )
    if duplicate:
        return {
            "status": "duplicate",
            "submission_id": str(duplicate.id),
            "transaction_id": str(duplicate.transaction_id) if duplicate.transaction_id else None,
        }

    accounts = (
        await s.execute(
            select(DirectPaymentAccount).where(
                DirectPaymentAccount.provider == provider,
                DirectPaymentAccount.currency == "BDT",
                DirectPaymentAccount.status == "active",
            )
        )
    ).scalars().all()
    receiver = _norm_number(receiver_number)
    account = next((a for a in accounts if _norm_number(a.account_number) == receiver), None)
    if not account:
        raise HTTPException(400, "receiver number is not a configured active Shopnoltd account")
    if account.verification_mode != "authorized_feed":
        raise HTTPException(409, "receiving account is not enabled for authorized feed verification")

    now = datetime.utcnow()
    intents = (
        await s.execute(
            select(DirectPaymentIntent)
            .where(
                DirectPaymentIntent.account_id == account.id,
                DirectPaymentIntent.provider == provider,
                DirectPaymentIntent.currency == "BDT",
                DirectPaymentIntent.status.in_(["awaiting_payment", "submitted", "verifying"]),
                DirectPaymentIntent.expires_at >= now,
                DirectPaymentIntent.amount == amount,
            )
            .order_by(DirectPaymentIntent.created_at.asc())
            .with_for_update()
        )
    ).scalars().all()

    # Exact amount + receiver can legitimately match more than one order.
    # Never guess in that situation; an administrator/customer can reconcile it.
    if len(intents) == 0:
        raise HTTPException(409, "no unique open payment intent matches this transaction")
    if len(intents) > 1:
        raise HTTPException(409, "multiple open payment intents match this transaction; automatic credit refused")
    intent = intents[0]

    wallet = await s.scalar(
        select(Wallet)
        .where(
            Wallet.tenant_id == intent.tenant_id,
            Wallet.user_id == intent.user_id,
            Wallet.currency == "BDT",
        )
        .with_for_update()
    )
    if not wallet:
        wallet = Wallet(
            tenant_id=intent.tenant_id,
            user_id=intent.user_id,
            currency="BDT",
            balance=0,
        )
        s.add(wallet)
        await s.flush()

    submission = DirectPaymentSubmission(
        intent_id=intent.id,
        provider=provider,
        txid=txid,
        sender_number=_norm_number(sender_number) if sender_number else None,
        amount_claimed=amount,
        raw_evidence={
            "receiver_number": receiver,
            "reference": reference,
            "occurred_at": occurred_at,
            "balance": balance,
            "raw_message": raw_message,
            "source_device": source_device,
            "verification": "signed_authorized_sms_feed",
        },
        verification_data={
            "mode": "signed_authorized_sms_feed",
            "receiver_account_id": str(account.id),
        },
        status="verified",
        verified_at=now,
    )
    s.add(submission)

    tx = Transaction(
        tenant_id=intent.tenant_id,
        user_id=intent.user_id,
        wallet_id=wallet.id,
        type=TxType.deposit,
        method=method,
        status=TxStatus.completed,
        amount=amount,
        fee=0,
        currency="BDT",
        external_id=txid,
        reference=reference or intent.expected_reference,
        meta={
            "direct_payment_intent_id": str(intent.id),
            "order_id": intent.order_id,
            "verification_mode": "signed_authorized_sms_feed",
            "receiver_account_id": str(account.id),
            "sender_number": _norm_number(sender_number) if sender_number else None,
            "occurred_at": occurred_at,
            "balance": balance,
            "source_device": source_device,
        },
        completed_at=now,
    )
    s.add(tx)
    wallet.balance = Decimal(str(wallet.balance)) + amount
    intent.status = "verified"
    submission.transaction_id = tx.id
    try:
        await s.flush()
        await s.commit()
    except IntegrityError as exc:
        await s.rollback()
        # The unique provider/TxID constraint is the final idempotency guard.
        duplicate = await s.scalar(
            select(DirectPaymentSubmission).where(
                DirectPaymentSubmission.provider == provider,
                DirectPaymentSubmission.txid == txid,
            )
        )
        if duplicate:
            return {
                "status": "duplicate",
                "submission_id": str(duplicate.id),
                "transaction_id": str(duplicate.transaction_id) if duplicate.transaction_id else None,
            }
        raise HTTPException(409, "direct payment feed could not be committed") from exc

    return {
        "status": "verified",
        "submission_id": str(submission.id),
        "transaction_id": str(tx.id),
        "intent_id": str(intent.id),
        "wallet_currency": wallet.currency,
        "credited_amount": str(amount),
    }


@router.post("/feed/{provider}")
async def receive_feed(
    provider: str,
    request: Request,
    x_shopno_relay_timestamp: str | None = Header(default=None),
    x_shopno_relay_signature: str | None = Header(default=None),
    x_shopno_relay_id: str | None = Header(default=None),
):
    provider = provider.lower().strip()
    if provider not in PROVIDERS:
        raise HTTPException(404, "unsupported direct MFS provider")
    if not x_shopno_relay_timestamp or not x_shopno_relay_signature:
        raise HTTPException(401, "relay signature headers are required")

    body = await request.body()
    _verify_signature(body, x_shopno_relay_timestamp, x_shopno_relay_signature)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(400, "invalid JSON feed payload") from exc

    if not isinstance(payload, dict):
        raise HTTPException(400, "feed payload must be an object")
    if str(payload.get("provider", provider)).lower() != provider:
        raise HTTPException(400, "provider mismatch")

    txid = str(payload.get("txid") or payload.get("trx_id") or payload.get("transaction_id") or "").strip()
    receiver = str(payload.get("receiver_number") or payload.get("to") or "").strip()
    sender = str(payload.get("sender_number") or payload.get("from") or "").strip() or None
    reference = str(payload.get("reference") or payload.get("ref") or "").strip() or None
    if not txid or len(txid) > 128:
        raise HTTPException(422, "provider transaction ID is required")
    if not receiver:
        raise HTTPException(422, "receiver_number is required")

    amount = _decimal(payload.get("amount"), "amount")
    currency = str(payload.get("currency", "BDT")).upper()
    if currency != "BDT":
        raise HTTPException(422, "direct MFS feed only supports BDT")

    async with SessionLocal() as s:
        result = await _credit_verified_feed(
            s,
            provider=provider,
            txid=txid,
            amount=amount,
            receiver_number=receiver,
            sender_number=sender,
            reference=reference,
            occurred_at=str(payload.get("occurred_at") or payload.get("datetime") or "") or None,
            raw_message=str(payload.get("raw_message") or "") or None,
            balance=str(payload.get("balance")) if payload.get("balance") is not None else None,
            source_device=x_shopno_relay_id,
        )
    return {"received": True, **result}
