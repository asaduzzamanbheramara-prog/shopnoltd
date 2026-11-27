import hashlib
from datetime import datetime
from decimal import Decimal
import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral import (
    Referral,
    ReferralCode,
    ReferralPolicy,
    ReferralReward,
    ReferralSystemIdentity,
)

ADMIN_OFFICE_ALIAS = "admin_office"

PAYMENTS = "http://payment-service.shopno-payments.svc.cluster.local:80"


async def resolve_referrer_recipient(s: AsyncSession, referrer_id: str, tenant_id: str) -> str:
    """Resolve platform aliases to a real Shopnoltd user before payment settlement."""
    alias = (referrer_id or "").strip()
    if not alias:
        raise HTTPException(409, "referral recipient is not configured")
    identity = await s.scalar(select(ReferralSystemIdentity).where(
        ReferralSystemIdentity.alias == alias,
        ReferralSystemIdentity.tenant_id == tenant_id,
        ReferralSystemIdentity.active == 1,
    ))
    if identity:
        if identity.user_id == alias:
            raise HTTPException(409, "referral recipient alias resolves to itself")
        return identity.user_id
    if alias != ADMIN_OFFICE_ALIAS:
        return alias
    raise HTTPException(409, "admin_office referral recipient is not configured to a real Shopnoltd user")


async def get_policy(s: AsyncSession, tenant_id: str, currency: str | None = None):
    policy = await s.scalar(select(ReferralPolicy).where(ReferralPolicy.tenant_id == tenant_id))
    if policy:
        return policy
    policy = ReferralPolicy(
        tenant_id=tenant_id,
        mode="percent",
        percent=Decimal("5"),
        fixed_amount=Decimal("0"),
        currency=currency or "MATCH_TASK",
        enabled=1,
        all_users_can_refer=1,
        fallback_referrer_id=ADMIN_OFFICE_ALIAS,
    )
    s.add(policy)
    await s.flush()
    return policy


async def ensure_fallback_referral(s: AsyncSession, referred_id: str, tenant_id: str, currency: str | None = None):
    """Keep an existing direct/legacy referral; otherwise bind the user to Admin Office."""
    existing = await s.scalar(select(Referral).where(Referral.referred_id == referred_id))
    if existing:
        return existing

    policy = await get_policy(s, tenant_id, currency)
    if not policy.enabled:
        return None

    fallback = (policy.fallback_referrer_id or "admin_office").strip()
    if not fallback or fallback == referred_id:
        return None

    await resolve_referrer_recipient(s, fallback, tenant_id)

    code = "ADMIN-" + hashlib.sha256(
        f"shopnoltd-admin-fallback:{fallback}".encode()
    ).hexdigest()[:12].upper()

    owner_code = await s.scalar(select(ReferralCode).where(ReferralCode.referrer_id == fallback))
    if not owner_code:
        owner_code = await s.scalar(select(ReferralCode).where(ReferralCode.code == code))
    if not owner_code:
        owner_code = ReferralCode(referrer_id=fallback, code=code)
        s.add(owner_code)
        await s.flush()

    referral = Referral(
        referrer_id=fallback,
        referred_id=referred_id,
        referral_code=owner_code.code,
        source="fallback",
        active=1,
    )
    s.add(referral)
    await s.flush()
    return referral



async def preflight_referral_reward(
    s: AsyncSession,
    referred_id: str,
    submission_id: str,
    base_amount: Decimal,
    currency: str,
    tenant_id: str,
    available_commission: Decimal,
) -> Decimal:
    """Validate referral recipient, currency and commission cap before any payout."""
    referral = await s.scalar(
        select(Referral).where(Referral.referred_id == referred_id, Referral.active == 1)
    )
    if not referral:
        referral = await ensure_fallback_referral(s, referred_id, tenant_id, currency)
    if not referral or referral.referrer_id == referred_id:
        return Decimal("0")

    existing = await s.scalar(select(ReferralReward).where(ReferralReward.submission_id == submission_id))
    if existing and existing.status == "settled":
        amount = Decimal(str(existing.reward_amount))
        reward_currency = str(existing.currency).upper()
    else:
        policy = await get_policy(s, tenant_id, currency)
        if not policy.enabled and not existing:
            return Decimal("0")
        if existing:
            amount = Decimal(str(existing.reward_amount))
            reward_currency = str(existing.currency).upper()
        else:
            amount = (
                Decimal(str(policy.fixed_amount))
                if policy.mode == "fixed"
                else base_amount * Decimal(str(policy.percent)) / Decimal("100")
            )
            if policy.max_amount is not None:
                amount = min(amount, Decimal(str(policy.max_amount)))
            reward_currency = str(policy.currency or "MATCH_TASK").upper()
            if reward_currency == "MATCH_TASK":
                reward_currency = currency
    amount = amount.quantize(Decimal("0.00000001"))
    if reward_currency != currency:
        raise HTTPException(409, "referral reward currency must match the completed task currency")
    if amount > available_commission:
        raise HTTPException(409, "configured referral reward exceeds the available Shopnoltd commission share")
    if amount > 0:
        recipient_alias = existing.referrer_id if existing else referral.referrer_id
        await resolve_referrer_recipient(s, recipient_alias, tenant_id)
    return amount


async def settle_referral_reward(
    s: AsyncSession,
    referred_id: str,
    work_id: str,
    submission_id: str,
    base_amount: Decimal,
    currency: str,
    tenant_id: str,
    token: str,
    available_commission: Decimal | None = None,
    payer_id: str | None = None,
):
    referral = await s.scalar(
        select(Referral).where(Referral.referred_id == referred_id, Referral.active == 1)
    )
    if not referral:
        referral = await ensure_fallback_referral(s, referred_id, tenant_id, currency)
    if not referral or referral.referrer_id == referred_id:
        return None

    existing = await s.scalar(select(ReferralReward).where(ReferralReward.submission_id == submission_id))
    if existing and existing.status == "settled":
        return existing

    policy = await get_policy(s, tenant_id, currency)
    if not policy.enabled and not existing:
        return None

    if existing:
        # A pending referral reward is an immutable settlement snapshot. Policy
        # edits must not change its amount or break an idempotent retry.
        amount = Decimal(str(existing.reward_amount)).quantize(Decimal("0.00000001"))
        reward_currency = str(existing.currency).upper()
    else:
        amount = (
            Decimal(str(policy.fixed_amount))
            if policy.mode == "fixed"
            else base_amount * Decimal(str(policy.percent)) / Decimal("100")
        )
        if policy.max_amount is not None:
            amount = min(amount, Decimal(str(policy.max_amount)))
        amount = amount.quantize(Decimal("0.00000001"))
        reward_currency = str(policy.currency or "MATCH_TASK").upper()
        if reward_currency == "MATCH_TASK":
            reward_currency = currency

    if available_commission is not None and amount > available_commission:
        raise HTTPException(409, "configured referral reward exceeds the available Shopnoltd commission share")
    if amount <= 0:
        return None
    if reward_currency != currency:
        raise HTTPException(409, "referral reward currency must match the completed task currency")

    if existing:
        reward = existing
    else:
        reward = ReferralReward(
            referral_id=referral.id,
            referred_id=referred_id,
            referrer_id=referral.referrer_id,
            work_id=work_id,
            submission_id=submission_id,
            base_amount=base_amount,
            reward_amount=amount,
            currency=reward_currency,
            status="pending",
        )
        s.add(reward)
        await s.flush()

    recipient_alias = existing.referrer_id if existing else referral.referrer_id
    recipient_id = await resolve_referrer_recipient(s, recipient_alias, tenant_id)
    if payer_id and recipient_id == payer_id:
        # A platform-office fallback attribution is already in the platform's own wallet when that office funded the task; do not self-transfer.
        reward.status = "settled"
        reward.payment_id = None
        reward.settled_at = datetime.utcnow()
        return reward
    key = "referral-settle:" + hashlib.sha256(submission_id.encode()).hexdigest()
    payload = {
        "to_user_id": recipient_id,
        "currency": reward_currency,
        "amount": float(amount),
        "note": f"referral:{submission_id}",
        "idempotency_key": key,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{PAYMENTS}/api/v1/transfers",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(
            503,
            "Referral reward payment service unavailable; completion remains pending",
        ) from exc

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise HTTPException(
            409,
            {
                "message": "Referral reward settlement failed; completion remains pending",
                "payment_error": detail,
            },
        )

    data = response.json() if response.text else {}
    reward.status = "settled"
    reward.payment_id = str(data.get("id") or data.get("transaction_id") or "") or None
    reward.settled_at = datetime.utcnow()
    return reward


async def settle_platform_commission(
    payer_id: str,
    recipient_id: str,
    submission_id: str,
    amount: Decimal,
    currency: str,
    token: str,
):
    """Move the remaining platform share to the configured Shopnoltd office account."""
    amount = Decimal(str(amount)).quantize(Decimal("0.00000001"))
    if amount <= 0 or recipient_id == payer_id:
        # If the platform office itself funded the task, its commission remains
        # in that wallet; the payment service correctly rejects self-transfers.
        return None
    key = "work-platform-commission:" + hashlib.sha256(submission_id.encode()).hexdigest()
    payload = {
        "to_user_id": recipient_id,
        "currency": currency,
        "amount": float(amount),
        "note": f"shopnoltd-platform-commission:{submission_id}",
        "idempotency_key": key,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{PAYMENTS}/api/v1/transfers",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Shopnoltd commission transfer unavailable; task remains pending") from exc
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise HTTPException(
            409,
            {
                "message": "Shopnoltd commission transfer failed; task remains pending",
                "payment_error": detail,
            },
        )
    return response.json() if response.text else {}


async def settle_referral_reward_from_work_escrow(
    s: AsyncSession, *, referred_id: str, work_id: str, submission_id: str,
    base_amount: Decimal, currency: str, tenant_id: str, available_commission: Decimal,
    payer_id: str, escrow_payout,
):
    """Create/settle the referral ledger entry using already-reserved task funds."""
    referral = await s.scalar(select(Referral).where(Referral.referred_id == referred_id, Referral.active == 1))
    if not referral:
        referral = await ensure_fallback_referral(s, referred_id, tenant_id, currency)
    if not referral or referral.referrer_id == referred_id:
        return None
    existing = await s.scalar(select(ReferralReward).where(ReferralReward.submission_id == submission_id))
    if existing and existing.status == "settled":
        return existing
    policy = await get_policy(s, tenant_id, currency)
    if not policy.enabled and not existing:
        return None
    if existing:
        amount = Decimal(str(existing.reward_amount)).quantize(Decimal("0.00000001"))
        reward_currency = str(existing.currency).upper()
        recipient_alias = existing.referrer_id
    else:
        amount = (Decimal(str(policy.fixed_amount)) if policy.mode == "fixed" else base_amount * Decimal(str(policy.percent)) / Decimal("100"))
        if policy.max_amount is not None:
            amount = min(amount, Decimal(str(policy.max_amount)))
        amount = amount.quantize(Decimal("0.00000001"))
        reward_currency = str(policy.currency or "MATCH_TASK").upper()
        if reward_currency == "MATCH_TASK":
            reward_currency = currency
        recipient_alias = referral.referrer_id
    if amount > available_commission:
        raise HTTPException(409, "configured referral reward exceeds the available Shopnoltd commission share")
    if reward_currency != currency:
        raise HTTPException(409, "referral reward currency must match the completed task currency")
    if amount <= 0:
        return None
    reward = existing or ReferralReward(
        referral_id=referral.id, referred_id=referred_id, referrer_id=referral.referrer_id,
        work_id=work_id, submission_id=submission_id, base_amount=base_amount,
        reward_amount=amount, currency=reward_currency, status="pending",
    )
    if not existing:
        s.add(reward)
        await s.flush()
    recipient_id = await resolve_referrer_recipient(s, recipient_alias, tenant_id)
    if recipient_id != payer_id:
        result = await escrow_payout(recipient_id, amount, f"referral:{submission_id}", f"referral:{submission_id}")
        reward.payment_id = str(result.get("transaction_id") or "") or None
    reward.status = "settled"
    reward.settled_at = datetime.utcnow()
    return reward


async def settle_platform_commission_from_work_escrow(
    *, payer_id: str, recipient_id: str, submission_id: str, amount: Decimal,
    escrow_payout,
):
    amount = Decimal(str(amount)).quantize(Decimal("0.00000001"))
    if amount <= 0 or recipient_id == payer_id:
        return None
    return await escrow_payout(recipient_id, amount, f"platform-commission:{submission_id}", f"shopnoltd-platform-commission:{submission_id}")
