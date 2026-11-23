"""Authenticated affiliate marketplace and click attribution.

Network conversion callbacks stay disabled until Affmine confirms the publisher
postback URL, secure-code mechanism, macros, and status lifecycle. No wallet
credit is performed by this API.
"""
import re
import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.affiliate import AffiliateClick, AffiliateConversion, AffiliateOffer

router = APIRouter(prefix="/affiliate", tags=["affiliate"])
bearer = HTTPBearer()
EXCHANGE_URL = "http://exchange-service.shopno-payments.svc.cluster.local:80"


async def db():
    async with SessionLocal() as session:
        yield session


async def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    claims = await verify_token(credentials.credentials)
    if not claims.get("sub"):
        raise HTTPException(401, "Authenticated user identity is missing")
    return claims


def _country(request: Request) -> str:
    value = (request.headers.get("cf-ipcountry") or "").upper()
    return value if re.fullmatch(r"[A-Z]{2}", value) and value != "XX" else ""


def _geo_ok(countries: str | None, country: str) -> bool:
    raw = (countries or "").strip().upper()
    if not raw or raw in {"ALL", "WORLDWIDE", "NULL", '""', "0"}:
        return True
    allowed = {part for part in re.split(r"[^A-Z]+", raw) if len(part) == 2}
    return bool(country and country in allowed)


def _safe_tracking_url(value: str, click_id: str) -> str:
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise HTTPException(503, "Offer tracking URL is not safely configured")
    if "{click_id}" in value:
        return value.replace("{click_id}", click_id)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["s1"] = click_id
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def _is_platform_admin(claims: dict) -> bool:
    roles = set((claims.get("realm_access") or {}).get("roles") or [])
    roles.update(claims.get("realm_roles") or [])
    return bool(roles.intersection({"platform_admin", "admin", "shopnoltd-admin"}))


def _require_admin(claims: dict):
    if not _is_platform_admin(claims):
        raise HTTPException(403, "Platform administrator realm role required")


def _percent(value, field="user_share_percent") -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise HTTPException(422, f"{field} must be an integer from 0 to 90")
    if number < 0 or number > 90:
        raise HTTPException(422, f"{field} must be between 0 and 90 so the platform retains at least 10%")
    return number


@router.get("/offers")
async def list_offers(request: Request, _user=Depends(current_user), session: AsyncSession = Depends(db)):
    country = _country(request)
    result = await session.execute(
        select(AffiliateOffer).where(
            AffiliateOffer.status == "active",
            AffiliateOffer.incentive_allowed.is_(True),
        ).order_by(AffiliateOffer.id.desc())
    )
    offers = []
    for offer in result.scalars().all():
        if not _geo_ok(offer.countries, country):
            continue
        user_share = Decimal(offer.user_share_percent) / Decimal(100)
        offers.append({
            "id": offer.id,
            "network_offer_id": offer.network_offer_id,
            "title": offer.title,
            "countries": offer.countries,
            "network_payout": str(offer.network_payout),
            "user_share_percent": offer.user_share_percent,
            "platform_share_percent": 100 - offer.user_share_percent,
            "estimated_user_reward": str((Decimal(offer.network_payout) * user_share).quantize(Decimal("0.0001"))),
            "currency": offer.currency,
        })
    return offers


@router.post("/offers/{offer_id}/start")
async def start_offer(offer_id: int, request: Request, claims=Depends(current_user), session: AsyncSession = Depends(db)):
    result = await session.execute(
        select(AffiliateOffer).where(
            AffiliateOffer.id == offer_id,
            AffiliateOffer.status == "active",
            AffiliateOffer.incentive_allowed.is_(True),
        )
    )
    offer = result.scalar_one_or_none()
    country = _country(request)
    if not offer or not _geo_ok(offer.countries, country):
        raise HTTPException(404, "Offer not available in your country")
    click_id = str(uuid.uuid4())
    session.add(AffiliateClick(
        id=click_id,
        user_id=str(claims["sub"]),
        offer_id=offer.id,
        country=country,
    ))
    await session.commit()
    # The returned URL is the user's unique network link. It can be copied/shared.
    return {"url": _safe_tracking_url(offer.tracking_url, click_id), "click_id": click_id}


@router.get("/me/summary")
async def my_summary(claims=Depends(current_user), session: AsyncSession = Depends(db)):
    user_id = str(claims["sub"])
    click_count = await session.scalar(
        select(func.count(AffiliateClick.id)).where(AffiliateClick.user_id == user_id)
    ) or 0
    conversion_rows = await session.execute(
        select(AffiliateConversion.status, func.count(AffiliateConversion.txn),
               func.coalesce(func.sum(AffiliateConversion.user_amount), 0))
        .join(AffiliateClick, AffiliateClick.id == AffiliateConversion.click_id)
        .where(AffiliateClick.user_id == user_id)
        .group_by(AffiliateConversion.status)
    )
    by_status = {status: {"count": int(count), "amount_usd": str(amount)}
                 for status, count, amount in conversion_rows.all()}
    return {
        "clicks": int(click_count),
        "conversions": sum(row["count"] for row in by_status.values()),
        "pending": by_status.get("pending", {"count": 0, "amount_usd": "0"}),
        "approved_unpaid": by_status.get("approved_unpaid", {"count": 0, "amount_usd": "0"}),
        "payable": by_status.get("payable", {"count": 0, "amount_usd": "0"}),
        "paid": by_status.get("paid", {"count": 0, "amount_usd": "0"}),
        "reversed": by_status.get("reversed", {"count": 0, "amount_usd": "0"}),
        "wallet_credit_enabled": False,
        "note": "Rewards remain pending until network approval and received payout are reconciled.",
    }


@router.get("/rates/usd-bdt")
async def usd_bdt_rate(_user=Depends(current_user)):
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(f"{EXCHANGE_URL}/api/v1/rates/USD/BDT")
            response.raise_for_status()
            data = response.json()
        rate = Decimal(str(data.get("rate", "0")))
        if rate <= 0:
            raise ValueError("non-positive exchange rate")
        return {"base": "USD", "quote": "BDT", "rate": str(rate),
                "source": data.get("source"), "fetched_at": data.get("fetched_at")}
    except (httpx.HTTPError, ValueError, TypeError, InvalidOperation) as exc:
        raise HTTPException(503, "A current USD/BDT rate is unavailable; no estimated conversion will be shown") from exc


@router.get("/admin/offers")
async def admin_offers(claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_admin(claims)
    result = await session.execute(select(AffiliateOffer).order_by(AffiliateOffer.id.desc()))
    return [
        {"id": o.id, "network_offer_id": o.network_offer_id, "title": o.title,
         "status": o.status, "incentive_allowed": o.incentive_allowed,
         "network_payout": str(o.network_payout), "currency": o.currency,
         "user_share_percent": o.user_share_percent,
         "platform_share_percent": 100 - o.user_share_percent, "countries": o.countries}
        for o in result.scalars().all()
    ]


@router.post("/admin/offers")
async def create_offer(request: Request, claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_admin(claims)
    body = await request.json()
    network_id = str(body.get("network_offer_id", "")).strip()
    title = str(body.get("title", "")).strip()
    tracking_url = str(body.get("tracking_url", "")).strip()
    if not network_id or len(network_id) > 128 or not title or len(title) > 500:
        raise HTTPException(422, "A valid network_offer_id and title are required")
    parts = urlsplit(tracking_url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise HTTPException(422, "A valid HTTPS tracking_url is required")
    try:
        payout = Decimal(str(body.get("network_payout", "0")))
    except InvalidOperation as exc:
        raise HTTPException(422, "network_payout must be a positive decimal") from exc
    if not payout.is_finite() or payout <= 0:
        raise HTTPException(422, "network_payout must be a positive decimal")
    existing = await session.scalar(select(AffiliateOffer).where(AffiliateOffer.network_offer_id == network_id))
    if existing:
        raise HTTPException(409, "This network offer already exists")
    share = _percent(body.get("user_share_percent", 70))
    offer = AffiliateOffer(
        network_offer_id=network_id,
        title=title,
        tracking_url=tracking_url,
        network_payout=payout,
        user_share_percent=share,
        incentive_allowed=body.get("incentive_allowed") is True,
        status="draft",
        countries=str(body.get("countries", "")).strip() or None,
        currency=str(body.get("currency", "USD")).upper(),
    )
    if offer.currency != "USD":
        raise HTTPException(422, "Only USD network payouts are supported until a verified network FX contract exists")
    session.add(offer)
    await session.commit()
    await session.refresh(offer)
    return {"id": offer.id, "status": offer.status, "incentive_allowed": offer.incentive_allowed,
            "user_share_percent": offer.user_share_percent, "platform_share_percent": 100 - offer.user_share_percent}


@router.patch("/admin/offers/{offer_id}/commission")
async def update_commission(offer_id: int, request: Request, claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_admin(claims)
    body = await request.json()
    offer = await session.get(AffiliateOffer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    offer.user_share_percent = _percent(body.get("user_share_percent"))
    await session.commit()
    return {"id": offer.id, "user_share_percent": offer.user_share_percent,
            "platform_share_percent": 100 - offer.user_share_percent}


@router.patch("/admin/offers/{offer_id}/eligibility")
async def update_offer_eligibility(offer_id: int, request: Request, claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_admin(claims)
    body = await request.json()
    allowed = body.get("incentive_allowed")
    if not isinstance(allowed, bool):
        raise HTTPException(422, "incentive_allowed must be true or false")
    offer = await session.get(AffiliateOffer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    offer.incentive_allowed = allowed
    if not allowed:
        offer.status = "paused"
    await session.commit()
    return {"id": offer.id, "incentive_allowed": offer.incentive_allowed, "status": offer.status}


@router.post("/admin/offers/{offer_id}/activate")
async def activate_offer(offer_id: int, claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_admin(claims)
    offer = await session.get(AffiliateOffer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    if not offer.incentive_allowed:
        raise HTTPException(422, "Advertiser incentive eligibility must be confirmed before activation")
    parts = urlsplit(offer.tracking_url)
    if parts.scheme != "https" or not parts.hostname:
        raise HTTPException(422, "Offer requires a valid HTTPS tracking URL")
    offer.status = "active"
    await session.commit()
    return {"id": offer.id, "status": offer.status}


@router.post("/admin/offers/{offer_id}/deactivate")
async def deactivate_offer(offer_id: int, claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_admin(claims)
    offer = await session.get(AffiliateOffer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    offer.status = "paused"
    await session.commit()
    return {"id": offer.id, "status": offer.status}


@router.get("/admin/summary")
async def admin_summary(claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_admin(claims)
    result = await session.execute(
        select(AffiliateConversion.status, func.count(AffiliateConversion.txn),
               func.coalesce(func.sum(AffiliateConversion.network_payout), 0),
               func.coalesce(func.sum(AffiliateConversion.user_amount), 0),
               func.coalesce(func.sum(AffiliateConversion.platform_amount), 0))
        .group_by(AffiliateConversion.status)
    )
    return {
        status: {"count": int(count), "network_payout_usd": str(network),
                 "user_share_usd": str(user), "platform_share_usd": str(platform)}
        for status, count, network, user, platform in result.all()
    }


@router.post("/postback", include_in_schema=False)
async def disabled_postback():
    raise HTTPException(503, "Callbacks disabled until Affmine confirms its publisher postback authentication, macros, and conversion status lifecycle")
