"""Direct-number payment workflow.

Supports bKash/Nagad/Rocket receiving accounts as Personal, Agent, or Merchant.
A customer TxID is never treated as proof by itself. Automatic verification is
only available when an authorized API/feed adapter is explicitly implemented;
otherwise the submission enters manual review.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.direct_payments import (
    DirectAccountStatus,
    DirectAccountType,
    DirectPaymentAccount,
    DirectPaymentIntent,
    DirectPaymentStatus,
    DirectPaymentSubmission,
    DirectVerificationMode,
)
from app.models.models import PaymentMethod, Transaction, TxStatus, TxType, Wallet
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
    roles = user.get("roles", [])
    if "platform_admin" not in roles and "admin" not in roles:
        raise HTTPException(403, "admin only")
    return user


class AccountIn(BaseModel):
    provider: str = Field(pattern="^(bkash|nagad|rocket)$")
    account_type: DirectAccountType
    account_number: str = Field(min_length=8, max_length=32)
    display_name: str = Field(min_length=1, max_length=128)
    currency: str = Field(min_length=3, max_length=8, default="BDT")
    verification_mode: DirectVerificationMode = DirectVerificationMode.manual
    instructions: str | None = None
    metadata: dict = Field(default_factory=dict)


class IntentIn(BaseModel):
    provider: str = Field(pattern="^(bkash|nagad|rocket)$")
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=8, default="BDT")
    order_id: str | None = Field(default=None, max_length=128)
    account_id: str | None = None
    expires_minutes: int = Field(default=30, ge=5, le=1440)


class SubmissionIn(BaseModel):
    sender_number: str | None = Field(default=None, max_length=32)
    transaction_id: str = Field(min_length=4, max_length=128)
    submitted_amount: Decimal = Field(gt=0)
    submitted_currency: str = Field(min_length=3, max_length=8, default="BDT")


class AdminVerifyIn(BaseModel):
    approved: bool
    reason: str = Field(min_length=3, max_length=500)


def account_out(a: DirectPaymentAccount) -> dict:
    return {
        "id": str(a.id),
        "provider": a.provider,
        "account_type": a.account_type.value,
        "account_number": a.account_number,
        "display_name": a.display_name,
        "currency": a.currency,
        "verification_mode": a.verification_mode.value,
        "status": a.status.value,
        "instructions": a.instructions,
    }


def intent_out(i: DirectPaymentIntent, a: DirectPaymentAccount) -> dict:
    return {
        "id": str(i.id),
        "order_id": i.order_id,
        "provider": i.provider,
        "amount": float(i.amount),
        "currency": i.currency,
        "status": i.status.value,
        "expires_at": i.expires_at.isoformat(),
        "expected_reference": i.expected_reference,
        "account": account_out(a),
    }


@router.get("/accounts")
async def list_accounts(user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    res = await s.execute(
        select(DirectPaymentAccount).where(
            DirectPaymentAccount.tenant_id == tenant_id,
            DirectPaymentAccount.status == DirectAccountStatus.active,
        ).order_by(DirectPaymentAccount.provider, DirectPaymentAccount.account_type)
    )
    return {"accounts": [account_out(a) for a in res.scalars().all()]}


@router.post("/accounts", status_code=201)
async def create_account(body: AccountIn, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    account = DirectPaymentAccount(
        tenant_id=user.get("tenant_id", "default"),
        provider=body.provider.lower(),
        account_type=body.account_type,
        account_number=body.account_number,
        display_name=body.display_name,
        currency=body.currency.upper(),
        verification_mode=body.verification_mode,
        instructions=body.instructions,
        metadata=body.metadata,
    )
    s.add(account)
    await s.commit()
    await s.refresh(account)
    return account_out(account)


@router.post("/intents", status_code=201)
async def create_intent(body: IntentIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    currency = body.currency.upper()
    query = select(DirectPaymentAccount).where(
        DirectPaymentAccount.tenant_id == tenant_id,
        DirectPaymentAccount.provider == body.provider.lower(),
        DirectPaymentAccount.currency == currency,
        DirectPaymentAccount.status == DirectAccountStatus.active,
    )
    if body.account_id:
        try:
            account_id = uuid.UUID(body.account_id)
        except ValueError as exc:
            raise HTTPException(400, "invalid account id") from exc
        query = query.where(DirectPaymentAccount.id == account_id)
    account = (await s.execute(query.order_by(DirectPaymentAccount.id))).scalars().first()
    if not account:
        raise HTTPException(404, "no active direct payment account configured")

    intent = DirectPaymentIntent(
        tenant_id=tenant_id,
        user_id=user["sub"],
        order_id=body.order_id,
        account_id=account.id,
        provider=account.provider,
        amount=body.amount,
        currency=currency,
        expected_reference=f"SHP-{uuid.uuid4().hex[:16].upper()}",
        status=DirectPaymentStatus.awaiting_payment,
        expires_at=datetime.utcnow() + timedelta(minutes=body.expires_minutes),
    )
    s.add(intent)
    await s.commit()
    await s.refresh(intent)
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
    if not account:
        raise HTTPException(500, "payment account missing")
    return intent_out(intent, account)


@router.post("/intents/{intent_id}/submit")
async def submit_payment(intent_id: str, body: SubmissionIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
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
    if intent.status not in (DirectPaymentStatus.awaiting_payment, DirectPaymentStatus.submitted, DirectPaymentStatus.manual_review):
        raise HTTPException(409, f"payment intent is {intent.status.value}")
    if datetime.utcnow() >= intent.expires_at:
        intent.status = DirectPaymentStatus.expired
        await s.commit()
        raise HTTPException(410, "payment intent expired")
    if body.submitted_currency.upper() != intent.currency:
        raise HTTPException(400, "currency mismatch")
    if body.submitted_amount != Decimal(str(intent.amount)):
        raise HTTPException(400, "amount mismatch")

    submission = DirectPaymentSubmission(
        intent_id=intent.id,
        provider=intent.provider,
        sender_number=body.sender_number,
        transaction_id=body.transaction_id,
        submitted_amount=body.submitted_amount,
        submitted_currency=body.submitted_currency.upper(),
        evidence={"expected_reference": intent.expected_reference},
        status=DirectPaymentStatus.submitted,
    )
    s.add(submission)
    try:
        await s.flush()
    except IntegrityError as exc:
        await s.rollback()
        raise HTTPException(409, "transaction ID has already been submitted") from exc

    account = await s.scalar(select(DirectPaymentAccount).where(DirectPaymentAccount.id == intent.account_id))
    if account and account.verification_mode in (DirectVerificationMode.authorized_api, DirectVerificationMode.authorized_feed):
        # Adapter hook: this status is deliberately not marked verified until an
        # authenticated provider adapter supplies transaction evidence.
        intent.status = DirectPaymentStatus.verifying
        submission.status = DirectPaymentStatus.verifying
        note = "submitted for authorized provider verification"
    else:
        intent.status = DirectPaymentStatus.manual_review
        submission.status = DirectPaymentStatus.manual_review
        note = "submitted for manual review; customer TxID is not payment proof"
    await s.commit()
    return {
        "ok": True,
        "submission_id": str(submission.id),
        "intent_id": str(intent.id),
        "status": intent.status.value,
        "automatic_verification": False,
        "note": note,
    }


@router.get("/admin/review")
async def review_queue(user=Depends(require_admin), s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(DirectPaymentSubmission, DirectPaymentIntent).join(
            DirectPaymentIntent, DirectPaymentIntent.id == DirectPaymentSubmission.intent_id
        ).where(
            DirectPaymentSubmission.status.in_([DirectPaymentStatus.manual_review, DirectPaymentStatus.verifying])
        ).order_by(DirectPaymentSubmission.created_at)
    )
    return {
        "items": [
            {
                "submission_id": str(sub.id),
                "intent_id": str(intent.id),
                "provider": sub.provider,
                "sender_number": sub.sender_number,
                "transaction_id": sub.transaction_id,
                "submitted_amount": float(sub.submitted_amount),
                "currency": sub.submitted_currency,
                "status": sub.status.value,
                "created_at": sub.created_at.isoformat(),
            }
            for sub, intent in res.all()
        ]
    }


@router.post("/admin/review/{submission_id}")
async def review_submission(submission_id: str, body: AdminVerifyIn, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    try:
        sid = uuid.UUID(submission_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid submission id") from exc
    submission = await s.scalar(select(DirectPaymentSubmission).where(DirectPaymentSubmission.id == sid))
    if not submission:
        raise HTTPException(404, "submission not found")
    intent = await s.scalar(select(DirectPaymentIntent).where(DirectPaymentIntent.id == submission.intent_id))
    if not intent:
        raise HTTPException(404, "payment intent not found")
    if submission.status == DirectPaymentStatus.verified:
        return {"ok": True, "status": "verified", "note": "already verified"}
    if not body.approved:
        submission.status = DirectPaymentStatus.failed
        intent.status = DirectPaymentStatus.failed
        submission.evidence = {**(submission.evidence or {}), "review_reason": body.reason, "reviewed_by": user["sub"]}
        await s.commit()
        return {"ok": True, "status": "failed"}

    if submission.submitted_amount != intent.amount or submission.submitted_currency != intent.currency:
        raise HTTPException(400, "cannot approve mismatched amount or currency")
    if datetime.utcnow() >= intent.expires_at:
        raise HTTPException(409, "payment intent expired")

    wallet = await s.scalar(select(Wallet).where(Wallet.user_id == intent.user_id, Wallet.currency == intent.currency))
    if not wallet:
        wallet = Wallet(tenant_id=intent.tenant_id, user_id=intent.user_id, currency=intent.currency, balance=0)
        s.add(wallet)
        await s.flush()

    idem = f"direct-payment:{submission.provider}:{submission.transaction_id}"
    tx = await s.scalar(select(Transaction).where(Transaction.idempotency_key == idem))
    if not tx:
        tx = Transaction(
            tenant_id=intent.tenant_id,
            user_id=intent.user_id,
            wallet_id=wallet.id,
            type=TxType.deposit,
            method=PaymentMethod(intent.provider),
            status=TxStatus.completed,
            amount=intent.amount,
            fee=0,
            currency=intent.currency,
            external_id=submission.transaction_id,
            reference=intent.expected_reference,
            idempotency_key=idem,
            meta={"source": "direct_number", "account_id": str(intent.account_id), "review_reason": body.reason},
            approved_by=user["sub"],
            completed_at=datetime.utcnow(),
        )
        s.add(tx)
        wallet.balance = Decimal(str(wallet.balance)) + Decimal(str(intent.amount))
    submission.status = DirectPaymentStatus.verified
    submission.verified_at = datetime.utcnow()
    submission.evidence = {**(submission.evidence or {}), "review_reason": body.reason, "reviewed_by": user["sub"]}
    intent.status = DirectPaymentStatus.verified
    await s.commit()
    return {"ok": True, "status": "verified", "transaction_id": str(tx.id)}
