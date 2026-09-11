"""Direct-number payment intents and evidence submission.

This flow deliberately separates customer-submitted evidence from proof of
payment. A submitted TxID never credits a wallet by itself. Only an authorized
provider verification result or an authenticated admin decision can transition
an intent to verified.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import DirectPaymentAccount, DirectPaymentIntent, DirectPaymentSubmission, PaymentMethod, Transaction, TxStatus, TxType, Wallet
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


async def require_admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    user = await verify_token(creds.credentials)
    if not ({"platform_admin", "admin"} & set(user.get("roles", []))):
        raise HTTPException(403, "admin only")
    return user


def intent_out(i: DirectPaymentIntent, account: DirectPaymentAccount | None = None):
    return {
        "id": str(i.id),
        "order_id": i.order_id,
        "provider": i.provider,
        "amount": float(i.amount),
        "currency": i.currency,
        "status": i.status,
        "expected_reference": i.expected_reference,
        "expires_at": i.expires_at.isoformat(),
        "account": {
            "id": str(account.id),
            "provider": account.provider,
            "account_type": account.account_type,
            "account_number": account.account_number,
            "display_name": account.display_name,
            "currency": account.currency,
            "instructions": account.instructions,
        } if account else None,
        "created_at": i.created_at.isoformat(),
    }


@router.get("/accounts")
async def accounts(provider: str | None = None, user=Depends(current_user), s: AsyncSession = Depends(db)):
    q = select(DirectPaymentAccount).where(
        DirectPaymentAccount.status == "active",
        DirectPaymentAccount.tenant_id == user.get("tenant_id", "default"),
    )
    if provider:
        q = q.where(DirectPaymentAccount.provider == provider.lower())
    rows = (await s.execute(q)).scalars().all()
    return {"accounts": [
        {"id": str(a.id), "provider": a.provider, "account_type": a.account_type,
         "account_number": a.account_number, "display_name": a.display_name,
         "currency": a.currency, "instructions": a.instructions}
        for a in rows
    ]}


@router.post("/intents", status_code=201)
async def create_intent(body: dict, user=Depends(current_user), s: AsyncSession = Depends(db)):
    provider = str(body.get("provider", "")).lower()
    currency = str(body.get("currency", "BDT")).upper()
    amount = Decimal(str(body.get("amount", "0")))
    if provider not in {"bkash", "nagad", "rocket"}:
        raise HTTPException(400, "direct payment supports bKash, Nagad and Rocket")
    if currency != "BDT" or amount <= 0:
        raise HTTPException(400, "direct payment currently requires a positive BDT amount")
    account_id = body.get("account_id")
    account = None
    if account_id:
        try:
            aid = uuid.UUID(account_id)
        except ValueError as exc:
            raise HTTPException(400, "invalid account_id") from exc
        account = await s.scalar(select(DirectPaymentAccount).where(
            DirectPaymentAccount.id == aid,
            DirectPaymentAccount.tenant_id == user.get("tenant_id", "default"),
            DirectPaymentAccount.status == "active",
        ))
    if not account:
        account = await s.scalar(select(DirectPaymentAccount).where(
            DirectPaymentAccount.provider == provider,
            DirectPaymentAccount.currency == currency,
            DirectPaymentAccount.tenant_id == user.get("tenant_id", "default"),
            DirectPaymentAccount.status == "active",
        ).order_by(DirectPaymentAccount.created_at.asc()))
    if not account:
        raise HTTPException(503, "no active receiving account is configured")
    if account.provider != provider or account.currency != currency:
        raise HTTPException(400, "account/provider/currency mismatch")

    iid = uuid.uuid4()
    reference = f"SHOPNO-{str(iid).replace('-', '')[:12].upper()}"
    intent = DirectPaymentIntent(
        id=iid, tenant_id=user.get("tenant_id", "default"), user_id=user["sub"],
        order_id=body.get("order_id"), account_id=account.id, provider=provider,
        amount=amount, currency=currency, expected_reference=reference,
        status="awaiting_payment", expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    s.add(intent)
    await s.commit()
    return intent_out(intent, account)


@router.get("/intents/{intent_id}")
async def get_intent(intent_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    try:
        iid = uuid.UUID(intent_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid intent id") from exc
    intent = await s.scalar(select(DirectPaymentIntent).where(
        DirectPaymentIntent.id == iid,
        DirectPaymentIntent.tenant_id == user.get("tenant_id", "default"),
        DirectPaymentIntent.user_id == user["sub"],
    ))
    if not intent:
        raise HTTPException(404, "payment intent not found")
    account = await s.scalar(select(DirectPaymentAccount).where(DirectPaymentAccount.id == intent.account_id))
    return intent_out(intent, account)


@router.post("/intents/{intent_id}/submit", status_code=201)
async def submit_evidence(intent_id: str, body: dict, user=Depends(current_user), s: AsyncSession = Depends(db)):
    try:
        iid = uuid.UUID(intent_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid intent id") from exc
    intent = await s.scalar(select(DirectPaymentIntent).where(
        DirectPaymentIntent.id == iid,
        DirectPaymentIntent.tenant_id == user.get("tenant_id", "default"),
        DirectPaymentIntent.user_id == user["sub"],
    ))
    if not intent:
        raise HTTPException(404, "payment intent not found")
    if intent.status not in {"awaiting_payment", "submitted", "verifying"}:
        raise HTTPException(400, "payment intent is not awaiting evidence")
    if datetime.utcnow() >= intent.expires_at:
        intent.status = "expired"
        await s.commit()
        raise HTTPException(400, "payment intent expired")
    txid = str(body.get("txid", "")).strip()
    sender = str(body.get("sender_number", "")).strip()
    if len(txid) < 4 or len(txid) > 128:
        raise HTTPException(422, "txid is required")
    existing = await s.scalar(select(DirectPaymentSubmission).where(DirectPaymentSubmission.txid == txid))
    if existing:
        raise HTTPException(409, "this TxID has already been submitted")
    submission = DirectPaymentSubmission(
        intent_id=intent.id, provider=intent.provider, txid=txid,
        sender_number=sender or None, amount_claimed=Decimal(str(body.get("amount", intent.amount))),
        raw_evidence={"reference": body.get("reference"), "sender_number": sender or None},
        status="submitted",
    )
    s.add(submission)
    intent.status = "submitted"
    await s.commit()
    return {"id": str(submission.id), "intent_id": str(intent.id), "status": submission.status,
            "message": "Evidence received. It will not be treated as proof until independently verified."}


@router.post("/submissions/{submission_id}/verify")
async def verify_submission(submission_id: str, body: dict, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    try:
        sid = uuid.UUID(submission_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid submission id") from exc
    sub = await s.scalar(select(DirectPaymentSubmission).where(DirectPaymentSubmission.id == sid))
    if not sub:
        raise HTTPException(404, "submission not found")
    if sub.status == "verified":
        return {"ok": True, "status": "verified", "transaction_id": str(sub.transaction_id) if sub.transaction_id else None}
    if not body.get("authorized_evidence", False):
        raise HTTPException(400, "verification requires an authorized provider result")
    if body.get("txid") and body["txid"] != sub.txid:
        raise HTTPException(400, "TxID mismatch")
    intent = await s.scalar(select(DirectPaymentIntent).where(DirectPaymentIntent.id == sub.intent_id).with_for_update())
    if not intent or intent.status == "expired":
        raise HTTPException(400, "payment intent is not valid")
    if Decimal(str(body.get("amount", intent.amount))) != Decimal(str(intent.amount)):
        sub.status = "failed"
        intent.status = "failed"
        await s.commit()
        raise HTTPException(400, "amount mismatch")
    receiver = str(body.get("receiver_number", "")).strip()
    account = await s.scalar(select(DirectPaymentAccount).where(DirectPaymentAccount.id == intent.account_id))
    if not account or receiver != account.account_number:
        raise HTTPException(400, "receiver account mismatch")
    wallet = await s.scalar(select(Wallet).where(Wallet.user_id == intent.user_id, Wallet.currency == intent.currency).with_for_update())
    if not wallet:
        wallet = Wallet(tenant_id=intent.tenant_id, user_id=intent.user_id, currency=intent.currency, balance=0)
        s.add(wallet)
        await s.flush()
    tx = Transaction(
        tenant_id=intent.tenant_id, user_id=intent.user_id, wallet_id=wallet.id,
        type=TxType.deposit, method=PaymentMethod(intent.provider), status=TxStatus.completed,
        amount=intent.amount, fee=0, currency=intent.currency, external_id=sub.txid,
        reference=intent.expected_reference, meta={"direct_payment_intent_id": str(intent.id), "verified_by": user["sub"], "verification_mode": "authorized_evidence"},
        approved_by=user["sub"], completed_at=datetime.utcnow(),
    )
    wallet.balance = Decimal(str(wallet.balance)) + intent.amount
    s.add(tx)
    sub.status = "verified"
    sub.transaction_id = tx.id
    sub.verified_at = datetime.utcnow()
    sub.verification_data = body
    intent.status = "verified"
    await s.commit()
    return {"ok": True, "status": "verified", "transaction_id": str(tx.id)}
