import hashlib
from datetime import datetime
from decimal import Decimal
import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral import Referral, ReferralPolicy, ReferralReward

PAYMENTS = "http://payment-service.shopno-payments.svc.cluster.local:80"

async def settle_referral_reward(s: AsyncSession, referred_id: str, work_id: str, submission_id: str, base_amount: Decimal, currency: str, tenant_id: str, token: str):
    referral = await s.scalar(select(Referral).where(Referral.referred_id == referred_id, Referral.active == 1))
    if not referral or referral.referrer_id == referred_id:
        return None
    existing = await s.scalar(select(ReferralReward).where(ReferralReward.submission_id == submission_id))
    if existing and existing.status == "settled":
        return existing
    policy = await s.scalar(select(ReferralPolicy).where(ReferralPolicy.tenant_id == tenant_id))
    if not policy:
        policy = ReferralPolicy(tenant_id=tenant_id, mode="percent", percent=Decimal("5"), fixed_amount=Decimal("0"), currency=currency, enabled=1)
        s.add(policy); await s.flush()
    if not policy.enabled:
        return None
    amount = Decimal(str(policy.fixed_amount)) if policy.mode == "fixed" else base_amount * Decimal(str(policy.percent)) / Decimal("100")
    if policy.max_amount is not None:
        amount = min(amount, Decimal(str(policy.max_amount)))
    amount = amount.quantize(Decimal("0.00000001"))
    if amount <= 0:
        return None
    reward_currency = str(policy.currency or currency).upper()
    if reward_currency != currency:
        raise HTTPException(409, "referral reward currency must match the completed task currency")
    if existing:
        reward = existing
    else:
        reward = ReferralReward(referral_id=referral.id, referred_id=referred_id, referrer_id=referral.referrer_id, work_id=work_id, submission_id=submission_id, base_amount=base_amount, reward_amount=amount, currency=reward_currency, status="pending")
        s.add(reward); await s.flush()
    key = "referral-settle:" + hashlib.sha256(submission_id.encode()).hexdigest()
    payload = {"to_user_id": referral.referrer_id, "currency": reward_currency, "amount": float(amount), "note": f"referral:{submission_id}", "idempotency_key": key}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{PAYMENTS}/api/v1/transfers", headers={"Authorization": f"Bearer {token}"}, json=payload)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Referral reward payment service unavailable; completion remains pending") from exc
    if response.status_code >= 400:
        try: detail = response.json()
        except Exception: detail = response.text
        raise HTTPException(409, {"message": "Referral reward settlement failed; completion remains pending", "payment_error": detail})
    data = response.json() if response.text else {}
    reward.status, reward.payment_id, reward.settled_at = "settled", str(data.get("id") or data.get("transaction_id") or "") or None, datetime.utcnow()
    return reward
