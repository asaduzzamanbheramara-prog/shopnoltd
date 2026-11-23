"""Affiliate offer browsing and click attribution.

Conversion callbacks remain disabled until Affmine confirms postback authentication
and exact parameter mapping. This module never credits a wallet.
"""
import re
import uuid
from decimal import Decimal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.affiliate import AffiliateClick, AffiliateOffer

router = APIRouter(prefix="/affiliate", tags=["affiliate"])
bearer = HTTPBearer()


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


@router.get("/offers")
async def list_offers(request: Request, _user=Depends(current_user), session: AsyncSession = Depends(db)):
    country = _country(request)
    result = await session.execute(
        select(AffiliateOffer).where(
            AffiliateOffer.status == "active",
            AffiliateOffer.incentive_allowed.is_(True),
        ).order_by(AffiliateOffer.id.desc())
    )
    return [
        {
            "id": offer.id,
            "title": offer.title,
            "countries": offer.countries,
            "reward": str((Decimal(offer.network_payout) * Decimal(offer.user_share_percent) / Decimal(100)).quantize(Decimal("0.0001"))),
            "currency": "USD",
        }
        for offer in result.scalars().all() if _geo_ok(offer.countries, country)
    ]


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
    session.add(AffiliateClick(id=click_id, user_id=str(claims["sub"]), offer_id=offer.id, country=country))
    await session.commit()
    return {"url": _safe_tracking_url(offer.tracking_url, click_id), "click_id": click_id}


@router.get("/admin/offers")
async def admin_offers(claims=Depends(current_user), session: AsyncSession = Depends(db)):
    if not _is_platform_admin(claims):
        raise HTTPException(403, "Platform administrator role required")
    result = await session.execute(select(AffiliateOffer).order_by(AffiliateOffer.id.desc()))
    return [
        {"id": offer.id, "network_offer_id": offer.network_offer_id, "title": offer.title,
         "status": offer.status, "incentive_allowed": offer.incentive_allowed,
         "user_share_percent": offer.user_share_percent, "countries": offer.countries}
        for offer in result.scalars().all()
    ]


@router.post("/admin/offers/{offer_id}/activate")
async def activate_offer(offer_id: int, claims=Depends(current_user), session: AsyncSession = Depends(db)):
    if not _is_platform_admin(claims):
        raise HTTPException(403, "Platform administrator role required")
    offer = await session.get(AffiliateOffer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    if not offer.incentive_allowed:
        raise HTTPException(422, "Advertiser has not confirmed incentive traffic for this offer")
    parts = urlsplit(offer.tracking_url)
    if parts.scheme != "https" or not parts.hostname:
        raise HTTPException(422, "Offer requires a valid HTTPS tracking URL")
    offer.status = "active"
    await session.commit()
    return {"id": offer.id, "status": offer.status}


@router.post("/admin/offers/{offer_id}/deactivate")
async def deactivate_offer(offer_id: int, claims=Depends(current_user), session: AsyncSession = Depends(db)):
    if not _is_platform_admin(claims):
        raise HTTPException(403, "Platform administrator role required")
    offer = await session.get(AffiliateOffer, offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found")
    offer.status = "paused"
    await session.commit()
    return {"id": offer.id, "status": offer.status}


@router.post("/postback", include_in_schema=False)
async def disabled_postback():
    raise HTTPException(503, "Callbacks disabled until Affmine postback authentication and parameter mapping are confirmed")
