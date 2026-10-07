import hashlib
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.referral import ReferralCode, Referral, ReferralPolicy, ReferralReward
from app.services.referrals import ensure_fallback_referral, get_policy

router = APIRouter(prefix="/referrals")
bearer = HTTPBearer()

PROFILE_CATEGORIES = {
    "data-management": "Data Management & Research",
    "interior-business": "Business & Interior Design",
}
MAX_SOURCE_LEN = 24

async def db():
    async with SessionLocal() as s:
        yield s

async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc

def is_admin(u):
    roles = set(u.get("roles") or [])
    realm = set(((u.get("realm_access") or {}).get("roles") or []))
    return bool(roles.intersection({"admin","platform_admin","shopnoltd-admin","administrator"}) or realm.intersection({"admin","platform_admin","shopnoltd-admin","administrator"}) or u.get("is_admin") is True)

def code_for(user_id: str) -> str:
    return "SNO-" + hashlib.sha256(("shopnoltd-referral:" + user_id).encode()).hexdigest()[:12].upper()

def referral_source(category: str | None) -> str:
    if not category:
        return "direct"
    category = str(category).strip().lower()
    if category not in PROFILE_CATEGORIES:
        raise HTTPException(422, "invalid referral profile category")
    value = f"direct:{category}"
    if len(value) > MAX_SOURCE_LEN:
        raise HTTPException(422, "referral profile category is too long")
    return value

async def ensure_code(s, user_id):
    row = await s.scalar(select(ReferralCode).where(ReferralCode.referrer_id == user_id))
    if row:
        return row.code
    code = code_for(user_id)
    row = ReferralCode(referrer_id=user_id, code=code)
    s.add(row)
    await s.commit()
    return code

@router.get("/me")
async def me(u=Depends(current_user), s: AsyncSession = Depends(db)):
    user_id = u["sub"]
    tenant = u.get("tenant_id") or u.get("tenant") or "default"
    policy = await get_policy(s, tenant)
    if not policy.enabled:
        raise HTTPException(403, "referral program is disabled by administrator")
    referral = await ensure_fallback_referral(s, user_id, tenant)
    await s.commit()
    if not policy.all_users_can_refer:
        existing_code = await s.scalar(select(ReferralCode).where(ReferralCode.referrer_id == user_id))
        if not existing_code:
            raise HTTPException(403, "referral access is not enabled for this user")
        code = existing_code.code
    else:
        code = await ensure_code(s, user_id)
    invited = int((await s.scalar(select(func.count(Referral.id)).where(Referral.referrer_id == user_id, Referral.active == 1))) or 0)
    rewards = (await s.execute(select(ReferralReward).where(ReferralReward.referrer_id == user_id).order_by(desc(ReferralReward.created_at)).limit(200))).scalars().all()
    return {
        "referral_code": code,
        "share_path": f"/register?ref={code}",
        "referred_users": invited,
        "pending_amount": str(sum((Decimal(str(x.reward_amount)) for x in rewards if x.status == "pending"), Decimal("0"))),
        "confirmed_amount": str(sum((Decimal(str(x.reward_amount)) for x in rewards if x.status == "settled"), Decimal("0"))),
        "attribution": {"referrer_id": referral.referrer_id if referral else None, "source": referral.source if referral else None},
        "is_admin": is_admin(u),
        "profile_categories": [{"slug": slug, "label": label} for slug, label in PROFILE_CATEGORIES.items()] if is_admin(u) else [],
        "rewards": [{"id": x.id, "work_id": x.work_id, "submission_id": x.submission_id, "amount": str(x.reward_amount), "currency": x.currency, "status": x.status, "created_at": x.created_at.isoformat()} for x in rewards],
    }

@router.post("/claim")
async def claim(body: dict, u=Depends(current_user), s: AsyncSession = Depends(db)):
    user_id = u["sub"]
    tenant = u.get("tenant_id") or u.get("tenant") or "default"
    policy = await get_policy(s, tenant)
    if not policy.enabled:
        raise HTTPException(403, "referral program is disabled by administrator")
    code = str(body.get("referral_code") or body.get("code") or "").strip().upper()
    if not code: raise HTTPException(422, "referral_code is required")
    category = body.get("profile_category") or body.get("category")
    source = referral_source(category)
    existing = await s.scalar(select(Referral).where(Referral.referred_id == user_id))
    if existing: return {"claimed": False, "already_claimed": True, "referrer_id": existing.referrer_id}
    owner = await s.scalar(select(ReferralCode).where(ReferralCode.code == code))
    if not owner: raise HTTPException(404, "referral code not found")
    if owner.referrer_id == user_id: raise HTTPException(400, "self-referral is not allowed")
    s.add(Referral(referrer_id=owner.referrer_id, referred_id=user_id, referral_code=code, source=source))
    await s.commit()
    return {"claimed": True, "referrer_id": owner.referrer_id, "profile_category": category}

@router.get("/admin/policy")
async def admin_policy(u=Depends(current_user), s: AsyncSession = Depends(db)):
    if not is_admin(u): raise HTTPException(403, "admin role required")
    tenant = u.get("tenant_id") or u.get("tenant") or "default"
    p = await s.scalar(select(ReferralPolicy).where(ReferralPolicy.tenant_id == tenant))
    if not p:
        p = ReferralPolicy(tenant_id=tenant, currency="MATCH_TASK")
        s.add(p); await s.commit(); await s.refresh(p)
    return {"tenant_id": p.tenant_id, "mode": p.mode, "percent": str(p.percent), "fixed_amount": str(p.fixed_amount), "max_amount": str(p.max_amount) if p.max_amount is not None else None, "currency": p.currency, "enabled": bool(p.enabled), "all_users_can_refer": bool(p.all_users_can_refer), "fallback_referrer_id": p.fallback_referrer_id}

@router.put("/admin/policy")
async def set_admin_policy(body: dict, u=Depends(current_user), s: AsyncSession = Depends(db)):
    if not is_admin(u): raise HTTPException(403, "admin role required")
    tenant = u.get("tenant_id") or u.get("tenant") or "default"
    mode = str(body.get("mode", "percent")).lower()
    if mode not in {"percent","fixed"}: raise HTTPException(422, "mode must be percent or fixed")
    percent, fixed = Decimal(str(body.get("percent", 5))), Decimal(str(body.get("fixed_amount", 0)))
    maximum = body.get("max_amount")
    maximum = Decimal(str(maximum)) if maximum not in (None, "") else None
    currency = str(body.get("currency", "MATCH_TASK")).upper()
    if percent < 0 or percent > 100 or fixed < 0 or (maximum is not None and maximum < 0): raise HTTPException(422, "invalid referral reward values")
    p = await get_policy(s, tenant, currency)
    p.mode, p.percent, p.fixed_amount, p.max_amount, p.currency, p.enabled = mode, percent, fixed, maximum, currency, 1 if body.get("enabled", True) else 0
    p.all_users_can_refer = 1 if body.get("all_users_can_refer", True) else 0
    p.fallback_referrer_id = str(body.get("fallback_referrer_id") or "admin_office").strip()
    if not p.fallback_referrer_id: raise HTTPException(422, "fallback_referrer_id is required")
    await s.commit(); await s.refresh(p)
    return {"updated": True, "mode": p.mode, "percent": str(p.percent), "fixed_amount": str(p.fixed_amount), "max_amount": str(p.max_amount) if p.max_amount is not None else None, "currency": p.currency, "enabled": bool(p.enabled), "all_users_can_refer": bool(p.all_users_can_refer), "fallback_referrer_id": p.fallback_referrer_id}

@router.get("/admin/rewards")
async def admin_rewards(u=Depends(current_user), s: AsyncSession = Depends(db)):
    if not is_admin(u): raise HTTPException(403, "admin role required")
    rows = (await s.execute(select(ReferralReward).order_by(desc(ReferralReward.created_at)).limit(500))).scalars().all()
    return [{"id": x.id, "referrer_id": x.referrer_id, "referred_id": x.referred_id, "work_id": x.work_id, "submission_id": x.submission_id, "base_amount": str(x.base_amount), "reward_amount": str(x.reward_amount), "currency": x.currency, "status": x.status, "payment_id": x.payment_id, "created_at": x.created_at.isoformat(), "settled_at": x.settled_at.isoformat() if x.settled_at else None} for x in rows]
