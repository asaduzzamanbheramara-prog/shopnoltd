"""Authenticated affiliate marketplace and click attribution.

Network conversion callbacks stay disabled until Affmine confirms the publisher
postback URL, secure-code mechanism, macros, and status lifecycle. No wallet
credit is performed by this API.
"""
import os
import re
import uuid
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.affiliate import AffiliateClick, AffiliateConversion, AffiliateOffer, AffiliateSandboxConversion

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



def _require_sandbox_enabled():
    if os.getenv("AFFILIATE_SANDBOX_ENABLED", "false").strip().lower() not in {"1", "true", "yes"}:
        raise HTTPException(404, "Affiliate sandbox is disabled in this environment")


def _country(request: Request) -> str:
    value = (request.headers.get("cf-ipcountry") or "").upper()
    return value if re.fullmatch(r"[A-Z]{2}", value) and value != "XX" else ""


def _geo_ok(countries: str | None, country: str) -> bool:
    raw = (countries or "").strip().upper()
    if not raw or raw in {"ALL", "WORLDWIDE", "NULL", '""', "0"}:
        return True
    allowed = {part for part in re.split(r"[^A-Z]+", raw) if len(part) == 2}
    return bool(country and country in allowed)


def _safe_tracking_url(value: str, click_id: str, click_param: str = "s1") -> str:
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise HTTPException(503, "Offer tracking URL is not safely configured")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", click_param or ""):
        raise HTTPException(503, "Offer click parameter is not safely configured")
    if "{click_id}" in value:
        return value.replace("{click_id}", click_id)
    # Preserve unrelated and repeated query parameters; replace only the
    # configured attribution parameter so each click has one unambiguous ID.
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
             if key != click_param]
    query.append((click_param, click_id))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def _is_platform_admin(claims: dict) -> bool:
    # Match the API's platform-wide authorization contract: only the
    # platform_admin realm role grants global affiliate administration.
    roles = set((claims.get("realm_access") or {}).get("roles") or [])
    roles.update(claims.get("realm_roles") or [])
    return "platform_admin" in roles


def _require_admin(claims: dict):
    if not _is_platform_admin(claims):
        raise HTTPException(403, "Platform administrator realm role required")


def _percent(value, field="user_share_percent") -> int:
    try:
        parsed = Decimal(str(value))
        if not parsed.is_finite() or parsed != parsed.to_integral_value():
            raise ValueError("not an integer")
        number = int(parsed)
    except (TypeError, ValueError, InvalidOperation):
        raise HTTPException(422, f"{field} must be an integer from 0 to 90")
    if number < 0 or number > 90:
        raise HTTPException(422, f"{field} must be between 0 and 90 so the platform retains at least 10%")
    return number


def _affmine_campaign_rows(payload, content_type: str):
    """Normalize Affmine v1 JSON/XML feed rows without trusting remote markup."""
    if "json" in (content_type or "").lower() or payload.lstrip().startswith("{"):
        import json
        data = json.loads(payload)
        root = data.get("offer_feed", data)
        if str(root.get("success", "true")).lower() not in {"true", "1", "yes"}:
            raise HTTPException(502, "Affmine campaign feed reported an unsuccessful response")
        offers = root.get("offers", [])
        if isinstance(offers, dict):
            offers = offers.get("offer", [])
        if isinstance(offers, dict):
            offers = [offers]
        return offers or []
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise HTTPException(502, "Affmine returned an invalid XML campaign feed") from exc
    if (root.findtext("success") or "true").lower() not in {"true", "1", "yes"}:
        raise HTTPException(502, "Affmine campaign feed reported an unsuccessful response")
    rows = []
    for node in root.findall("./offers/offer"):
        row = {child.tag: child.text or "" for child in node if child.tag != "countries"}
        row["countries"] = [
            {"country_code": country.findtext("country_code", ""),
             "country_name": country.findtext("country_name", "")}
            for country in node.findall("./countries/country")
        ]
        rows.append(row)
    return rows


def _affmine_platform_codes(value):
    """Normalize Affmine platform IDs: 1 Windows, 2 Mac, 3 Android, 4 iOS, 5 other mobile."""
    if isinstance(value, list):
        raw = ",".join(str(item.get("platform_id", item.get("id", ""))) if isinstance(item, dict) else str(item) for item in value)
    else:
        raw = str(value or "")
    named = {"WINDOWS": "1", "MAC": "2", "MACOS": "2", "ANDROID": "3",
             "IOS": "4", "IPHONE": "4", "IPAD": "4", "OTHER MOBILE": "5",
             "OTHER_MOBILE": "5", "MOBILE": "5"}
    for label, code in named.items():
        raw = re.sub(rf"\b{re.escape(label)}\b", code, raw, flags=re.IGNORECASE)
    codes = sorted({part for part in re.split(r"[^0-9]+", raw) if part in {"1", "2", "3", "4", "5"}}, key=int)
    return ",".join(codes) if codes else "unknown"


def _client_platform(request: Request) -> str:
    ua = (request.headers.get("user-agent") or "").lower()
    if "android" in ua:
        return "3"
    if any(token in ua for token in ("iphone", "ipad", "ipod")):
        return "4"
    if "windows" in ua:
        return "1"
    if any(token in ua for token in ("macintosh", "mac os")):
        return "2"
    if any(token in ua for token in ("mobile", "opera mini", "iemobile")):
        return "5"
    return ""


def _platform_ok(allowed_platform: str | None, client_platform: str) -> bool:
    raw = (allowed_platform or "").strip()
    if raw in {"", "0", "ALL", "1,2,3,4,5"}:
        return True
    allowed = {part for part in raw.split(",") if part in {"1", "2", "3", "4", "5"}}
    return bool(client_platform and client_platform in allowed)


def _affmine_country_codes(value):
    if isinstance(value, list):
        codes = [str(row.get("country_code", "")).upper() for row in value if isinstance(row, dict)]
        return ",".join(code for code in codes if re.fullmatch(r"[A-Z]{2}", code)) or None
    raw = str(value or "").strip().upper()
    if raw in {"", "0", "ALL", "WORLDWIDE"}:
        return None
    codes = [part for part in re.split(r"[^A-Z]+", raw) if re.fullmatch(r"[A-Z]{2}", part)]
    return ",".join(codes) or None


@router.get("/offers")
async def list_offers(request: Request, _user=Depends(current_user), session: AsyncSession = Depends(db)):
    country = _country(request)
    platform = _client_platform(request)
    result = await session.execute(
        select(AffiliateOffer).where(
            AffiliateOffer.status == "active",
            AffiliateOffer.incentive_allowed.is_(True),
        ).order_by(AffiliateOffer.id.desc())
    )
    offers = []
    for offer in result.scalars().all():
        if not _geo_ok(offer.countries, country) or not _platform_ok(offer.allowed_platform, platform):
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
            "allowed_platform": offer.allowed_platform,
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
    platform = _client_platform(request)
    if not offer or not _geo_ok(offer.countries, country) or not _platform_ok(offer.allowed_platform, platform):
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
    return {"url": _safe_tracking_url(offer.tracking_url, click_id, offer.click_param), "click_id": click_id}


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


@router.post("/admin/sync-affmine")
async def sync_affmine_campaigns(claims=Depends(current_user), session: AsyncSession = Depends(db)):
    """Import Affmine active campaigns as inactive drafts; never auto-enable rewards."""
    _require_admin(claims)
    aff_id = os.getenv("AFFMINE_AFF_ID", "").strip()
    api_key = os.getenv("AFFMINE_API_KEY", "").strip()
    if not aff_id or not api_key:
        raise HTTPException(503, "Affmine API credentials are not configured on the API service")
    inserted = updated = skipped_currency = 0
    start_row = 0
    page_size = 200
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            while True:
                response = await client.get(
                    "https://network.affmine.com/api/v1/getCampaigns",
                    params={
                        "aff_id": aff_id, "api_key": api_key, "format": "json",
                        "offer_status": "1", "countries": "0",
                        "platform": "1,2,3,4,5", "incentive": "0",
                        "start_row": str(start_row), "limit_row": str(page_size),
                    },
                )
                response.raise_for_status()
                rows = _affmine_campaign_rows(response.text, response.headers.get("content-type", ""))
                if not rows:
                    break
                for row in rows:
                    network_id = str(row.get("offer_id", "")).strip()
                    title = str(row.get("offer_name", "")).strip()
                    if not network_id or not title:
                        continue
                    currency = str(row.get("currency", "USD")).strip().upper()
                    if not re.fullmatch(r"[A-Z]{3}", currency):
                        skipped_currency += 1
                        continue
                    try:
                        payout = Decimal(str(row.get("payout", "0")))
                    except (InvalidOperation, TypeError, ValueError):
                        continue
                    if not payout.is_finite() or payout <= 0:
                        continue
                    existing = await session.scalar(
                        select(AffiliateOffer).where(AffiliateOffer.network_offer_id == network_id)
                    )
                    tracking_url = str(row.get("url", "") or "").strip()
                    if tracking_url and (urlsplit(tracking_url).scheme != "https" or not urlsplit(tracking_url).hostname):
                        tracking_url = ""
                    countries = _affmine_country_codes(row.get("countries"))
                    allowed_platform = _affmine_platform_codes(row.get("allowed_platform"))
                    network_incentive = str(row.get("incentive", "unknown")).strip().lower()[:16] or "unknown"
                    if existing:
                        existing.title = title[:500]
                        existing.network_payout = payout
                        existing.currency = currency
                        existing.countries = countries
                        existing.allowed_platform = allowed_platform
                        existing.network_incentive = network_incentive
                        if tracking_url:
                            existing.tracking_url = tracking_url
                        # Keep existing admin decision/status unchanged on sync.
                        updated += 1
                    else:
                        session.add(AffiliateOffer(
                            network_offer_id=network_id[:128], title=title[:500],
                            tracking_url=tracking_url, click_param="s1",
                            network_payout=payout, user_share_percent=70,
                            incentive_allowed=False, status="draft",
                            countries=countries, currency=currency,
                            allowed_platform=allowed_platform, network_incentive=network_incentive,
                        ))
                        inserted += 1
                await session.commit()
                if len(rows) < page_size:
                    break
                start_row += page_size
    except httpx.HTTPStatusError as exc:
        await session.rollback()
        raise HTTPException(502, f"Affmine API returned HTTP {exc.response.status_code}") from exc
    except (httpx.HTTPError, ValueError, InvalidOperation) as exc:
        await session.rollback()
        raise HTTPException(502, "Could not retrieve or parse Affmine campaign feed") from exc
    return {
        "source": "Affmine Publisher API v1.0", "status": "imported_as_drafts",
        "inserted": inserted, "updated": updated, "skipped_invalid_currency": skipped_currency,
        "incentives_enabled": 0, "offers_activated": 0,
        "note": "Imported campaigns remain Draft and incentive-disabled until campaign-level permission and tracking parameters are verified.",
    }


@router.get("/admin/offers")
async def admin_offers(claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_admin(claims)
    result = await session.execute(select(AffiliateOffer).order_by(AffiliateOffer.id.desc()))
    return [
        {"id": o.id, "network_offer_id": o.network_offer_id, "title": o.title,
         "status": o.status, "incentive_allowed": o.incentive_allowed,
         "network_payout": str(o.network_payout), "currency": o.currency,
         "user_share_percent": o.user_share_percent,
         "platform_share_percent": 100 - o.user_share_percent, "countries": o.countries,
         "allowed_platform": o.allowed_platform, "network_incentive": o.network_incentive}
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
    click_param = str(body.get("click_param", "s1")).strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", click_param):
        raise HTTPException(422, "click_param must be a valid confirmed network sub-ID parameter")
    offer = AffiliateOffer(
        network_offer_id=network_id,
        title=title,
        tracking_url=tracking_url,
        click_param=click_param,
        network_payout=payout,
        user_share_percent=share,
        incentive_allowed=body.get("incentive_allowed") is True,
        status="draft",
        countries=str(body.get("countries", "")).strip() or None,
        currency=str(body.get("currency", "USD")).strip().upper(),
        allowed_platform=_affmine_platform_codes(body.get("allowed_platform", "1,2,3,4,5")),
        network_incentive="unknown",
    )
    if not re.fullmatch(r"[A-Z]{3}", offer.currency):
        raise HTTPException(422, "currency must be a three-letter ISO currency code")
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



# Sandbox records are separate from network conversions and never settle to wallets.
@router.post("/sandbox/simulate")
async def simulate_sandbox_earning(request: Request, claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_sandbox_enabled()
    body = await request.json()
    try:
        payout = Decimal(str(body.get("network_payout_usd", "1")))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HTTPException(422, "network_payout_usd must be a positive decimal") from exc
    if not payout.is_finite() or payout <= 0 or payout > Decimal("1000"):
        raise HTTPException(422, "Sandbox payout must be greater than 0 and no more than 1000 USD")
    share = _percent(body.get("user_share_percent", 70))
    user_amount = (payout * Decimal(share) / Decimal(100)).quantize(Decimal("0.0001"))
    platform_amount = (payout - user_amount).quantize(Decimal("0.0001"))
    record = AffiliateSandboxConversion(
        id=str(uuid.uuid4()), user_id=str(claims["sub"]),
        simulated_network_payout=payout.quantize(Decimal("0.0001")),
        simulated_user_amount=user_amount, simulated_platform_amount=platform_amount,
        user_share_percent=share, currency="USD",
    )
    session.add(record)
    await session.commit()
    return {
        "id": record.id, "sandbox": True, "enabled": True, "withdrawable": False, "wallet_credited": False,
        "currency": "USD", "simulated_network_payout": str(record.simulated_network_payout),
        "simulated_user_amount": str(record.simulated_user_amount),
        "simulated_platform_amount": str(record.simulated_platform_amount),
        "user_share_percent": share, "platform_share_percent": 100 - share,
        "note": "Simulation only. Not an Affmine conversion, real income, or payable balance.",
    }


@router.get("/sandbox/me/summary")
async def sandbox_user_summary(claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_sandbox_enabled()
    result = await session.execute(
        select(func.count(AffiliateSandboxConversion.id),
               func.coalesce(func.sum(AffiliateSandboxConversion.simulated_network_payout), 0),
               func.coalesce(func.sum(AffiliateSandboxConversion.simulated_user_amount), 0))
        .where(AffiliateSandboxConversion.user_id == str(claims["sub"]))
    )
    count, network, user_amount = result.one()
    return {
        "sandbox": True, "enabled": True, "withdrawable": False, "wallet_credited": False,
        "conversions": int(count), "simulated_network_payout_usd": str(network),
        "simulated_user_amount_usd": str(user_amount),
        "note": "Simulation only; excluded from real earnings and wallet balance.",
    }


@router.delete("/sandbox/me/reset")
async def reset_my_sandbox(claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_sandbox_enabled()
    result = await session.execute(
        delete(AffiliateSandboxConversion).where(AffiliateSandboxConversion.user_id == str(claims["sub"]))
    )
    await session.commit()
    return {"sandbox": True, "deleted_test_records": result.rowcount or 0, "wallet_unchanged": True}


@router.get("/sandbox/admin/summary")
async def sandbox_admin_summary(claims=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_sandbox_enabled()
    _require_admin(claims)
    result = await session.execute(
        select(func.count(AffiliateSandboxConversion.id),
               func.coalesce(func.sum(AffiliateSandboxConversion.simulated_network_payout), 0),
               func.coalesce(func.sum(AffiliateSandboxConversion.simulated_user_amount), 0),
               func.coalesce(func.sum(AffiliateSandboxConversion.simulated_platform_amount), 0))
    )
    count, network, users, platform = result.one()
    return {
        "sandbox": True, "enabled": True, "withdrawable": False, "wallet_credited": False,
        "test_conversions": int(count), "simulated_network_payout_usd": str(network),
        "simulated_user_share_usd": str(users), "simulated_platform_share_usd": str(platform),
        "note": "Simulated values only; excluded from real revenue, payable earnings, and wallet balances.",
    }


@router.post("/postback", include_in_schema=False)
async def disabled_postback():
    raise HTTPException(503, "Callbacks disabled until Affmine confirms its publisher postback authentication, macros, and conversion status lifecycle")

[executed on device: Shopnoltd (52cb1894-787c-49c2-9460-901a8f74a1e7)]