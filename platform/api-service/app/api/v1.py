"""Versioned REST facade that aggregates downstream services."""

import math
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.financial_registry import (
    CURRENCY_REGISTRY,
    PAYOUT_PROVIDERS,
    capability_matrix,
    gateway_catalog,
    payment_method_catalog,
)
from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()

PAYMENTS_BASE = "http://billing-engine.shopno-payments.svc.cluster.local:80"
EXCHANGE_BASE = "http://exchange-service.shopno-payments.svc.cluster.local:80"


async def user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return await verify_token(creds.credentials)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from e


async def call(method: str, url: str, user_token: str, **kw):
    headers = {"Authorization": f"Bearer {user_token}"}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.request(method, url, headers=headers, **kw)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
        raise HTTPException(status_code=503, detail="Downstream service unavailable") from e
    if r.status_code >= 400:
        detail = r.text
        try:
            detail = r.json()
        except Exception:
            pass
        raise HTTPException(status_code=r.status_code, detail=detail)
    return r.json() if r.text else None


def _runtime_gateway_rows(downstream: dict | None) -> list[dict]:
    runtime_rows = downstream.get("gateways", []) if isinstance(downstream, dict) else []
    runtime = {
        str(row.get("name", "")).strip().lower(): row
        for row in runtime_rows
        if isinstance(row, dict) and str(row.get("name", "")).strip()
    }
    normalized = []
    for gateway_id, definition in gateway_catalog().items():
        source = runtime.get(gateway_id, {})
        configured = bool(source.get("credentials_configured"))
        admin_disabled = bool(source.get("admin_disabled"))
        provider_live = bool(source.get("effectively_live", source.get("live")))
        implemented = bool(definition.get("implemented"))
        provider_supported = bool(definition.get("provider_supported"))
        available = implemented and provider_supported and not admin_disabled and configured and provider_live
        if not provider_supported:
            status = "unsupported"
        elif not implemented:
            status = "adapter_not_implemented"
        elif admin_disabled:
            status = "disabled"
        elif not configured:
            status = "not_configured"
        elif not provider_live:
            status = "unavailable"
        else:
            status = "available"
        normalized.append({
            **definition,
            "enabled": not admin_disabled and implemented,
            "configured": configured,
            "available": available,
            "activation_required": provider_supported and (not configured or not implemented),
            "status": status,
            "credentials_configured": configured,
            "admin_disabled": admin_disabled,
            "provider_live": provider_live,
        })
    return normalized


async def _authoritative_settlement_amount(
    *, base_amount: float, base_currency: str, settlement_currency: str, user_token: str
) -> tuple[float, float, dict]:
    """Convert the service/base price server-side; never trust a browser conversion."""
    if not math.isfinite(base_amount) or base_amount <= 0:
        raise HTTPException(status_code=422, detail={"code": "INVALID_BASE_AMOUNT", "amount": base_amount})
    base_currency = base_currency.strip().upper()
    settlement_currency = settlement_currency.strip().upper()
    if not base_currency or not settlement_currency:
        raise HTTPException(status_code=422, detail={"code": "INVALID_CURRENCY"})
    if base_currency == settlement_currency:
        return round(base_amount, 2), 1.0, {"live": True, "source": "identity"}
    rate_data = await call(
        "GET",
        f"{EXCHANGE_BASE}/api/v1/rates/{quote(base_currency, safe='')}/{quote(settlement_currency, safe='')}",
        user_token,
    )
    try:
        rate = float(rate_data["rate"])
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=502, detail={"code": "FX_RATE_INVALID"}) from e
    if not math.isfinite(rate) or rate <= 0:
        raise HTTPException(status_code=502, detail={"code": "FX_RATE_INVALID"})
    converted = round(base_amount * rate, 2)
    if not math.isfinite(converted) or converted <= 0:
        raise HTTPException(status_code=502, detail={"code": "FX_CONVERSION_INVALID"})
    return converted, rate, rate_data


@router.get("/me")
async def me(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await user(creds)


@router.get("/users/me")
async def users_me(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await user(creds)


@router.get("/financial/capabilities")
async def financial_capabilities(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    await user(creds)
    gateways_response = await call("GET", f"{PAYMENTS_BASE}/gateways", creds.credentials)
    return {
        "version": 4,
        "currencies": CURRENCY_REGISTRY,
        "payment_methods": list(payment_method_catalog().values()),
        "gateways": _runtime_gateway_rows(gateways_response),
        "payout_providers": list(PAYOUT_PROVIDERS.values()),
        "capability_matrix": capability_matrix(),
    }


@router.get("/financial/capability-matrix")
async def financial_capability_matrix(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    await user(creds)
    items = capability_matrix()
    return {"version": 1, "items": items, "count": len(items)}


@router.get("/wallet")
async def wallet(currency: str | None = Query(default=None), creds: HTTPAuthorizationCredentials = Depends(bearer)):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")
    query = f"?currency={quote(currency.upper(), safe='')}" if currency else ""
    return await call("GET", f"{PAYMENTS_BASE}/wallet/{quote(email, safe='')}{query}", creds.credentials)


@router.get("/wallet/ledger")
async def wallet_ledger(currency: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=200), creds: HTTPAuthorizationCredentials = Depends(bearer)):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")
    params = [f"limit={limit}"]
    if currency:
        params.append(f"currency={quote(currency.upper(), safe='')}")
    return await call("GET", f"{PAYMENTS_BASE}/wallet/{quote(email, safe='')}/ledger?{'&'.join(params)}", creds.credentials)


@router.get("/wallet/{currency}")
async def wallet_by_currency(currency: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await wallet(currency=currency, creds=creds)


@router.get("/transactions")
async def transactions(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), creds: HTTPAuthorizationCredentials = Depends(bearer)):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")
    data = await call("GET", f"{PAYMENTS_BASE}/transactions/{quote(email, safe='')}", creds.credentials)
    items = data if isinstance(data, list) else []
    page = items[offset:offset + limit]
    return {"items": page, "limit": limit, "offset": offset, "count": len(page), "total": len(items), "has_more": offset + limit < len(items)}


@router.get("/feed")
async def feed(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", "http://social-service.shopno-platform.svc.cluster.local:80/api/v1/feed/me", creds.credentials)


@router.get("/conversations")
async def conversations(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", "http://messaging-service.shopno-platform.svc.cluster.local:80/api/v1/conversations", creds.credentials)


@router.get("/notifications")
async def notifications(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", "http://notification-service.shopno-platform.svc.cluster.local:80/api/v1/notifications/me", creds.credentials)


@router.get("/billing/gateways")
async def billing_gateways(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await financial_capabilities(creds)


@router.post("/billing/checkout")
async def billing_checkout(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")

    currency = str(body.get("currency") or "").strip().upper()
    gateway = str(body.get("gateway") or "").strip().lower()
    base_currency = str(body.get("base_currency") or "").strip().upper()
    base_amount_raw = body.get("base_amount")
    amount_raw = body.get("amount")
    if not currency or not gateway:
        raise HTTPException(status_code=422, detail={"code": "INVALID_CHECKOUT_REQUEST", "message": "gateway and currency are required"})

    if base_amount_raw is not None:
        try:
            base_amount = float(base_amount_raw)
        except (TypeError, ValueError) as e:
            raise HTTPException(status_code=422, detail={"code": "INVALID_BASE_AMOUNT"}) from e
        if not base_currency:
            raise HTTPException(status_code=422, detail={"code": "INVALID_CHECKOUT_REQUEST", "message": "base_currency is required with base_amount"})
        amount_number, fx_rate, fx_meta = await _authoritative_settlement_amount(
            base_amount=base_amount,
            base_currency=base_currency,
            settlement_currency=currency,
            user_token=creds.credentials,
        )
        if amount_raw is not None:
            try:
                client_amount = float(amount_raw)
            except (TypeError, ValueError) as e:
                raise HTTPException(status_code=422, detail={"code": "INVALID_AMOUNT"}) from e
            if not math.isfinite(client_amount) or client_amount <= 0:
                raise HTTPException(status_code=422, detail={"code": "INVALID_AMOUNT"})
            if abs(round(client_amount, 2) - amount_number) > 0.01:
                raise HTTPException(status_code=409, detail={"code": "CHECKOUT_AMOUNT_MISMATCH", "expected_amount": amount_number, "currency": currency, "base_amount": base_amount, "base_currency": base_currency, "rate": fx_rate})
        pricing = {"base_amount": round(base_amount, 2), "base_currency": base_currency, "settlement_amount": amount_number, "settlement_currency": currency, "fx_rate": fx_rate, "fx": fx_meta}
    else:
        if amount_raw is None:
            raise HTTPException(status_code=422, detail={"code": "INVALID_CHECKOUT_REQUEST", "message": "amount or base_amount is required"})
        try:
            amount_number = float(amount_raw)
        except (TypeError, ValueError) as e:
            raise HTTPException(status_code=422, detail={"code": "INVALID_AMOUNT"}) from e
        if not math.isfinite(amount_number) or amount_number <= 0:
            raise HTTPException(status_code=422, detail={"code": "INVALID_AMOUNT", "amount": amount_raw})
        pricing = {"settlement_amount": amount_number, "settlement_currency": currency, "pricing_source": "explicit_settlement_amount"}

    capability = await call("GET", f"{PAYMENTS_BASE}/gateways", creds.credentials)
    gateway_row = next((g for g in _runtime_gateway_rows(capability) if g["id"] == gateway), None)
    if gateway_row is None:
        raise HTTPException(status_code=422, detail={"code": "GATEWAY_UNSUPPORTED", "gateway": gateway})
    if gateway_row.get("currency_mode") != "provider_defined" and currency not in set(gateway_row["currencies"]):
        raise HTTPException(status_code=422, detail={"code": "GATEWAY_CURRENCY_UNSUPPORTED", "gateway": gateway, "currency": currency, "supported_currencies": gateway_row["currencies"]})
    if gateway_row["status"] == "disabled":
        raise HTTPException(status_code=503, detail={"code": "GATEWAY_DISABLED", "gateway": gateway})
    if gateway_row["status"] == "not_configured":
        raise HTTPException(status_code=503, detail={"code": "GATEWAY_NOT_CONFIGURED", "gateway": gateway})
    if gateway_row["status"] == "adapter_not_implemented":
        raise HTTPException(status_code=503, detail={"code": "GATEWAY_UNAVAILABLE", "gateway": gateway, "reason": "adapter_not_implemented"})
    if not gateway_row["available"]:
        raise HTTPException(status_code=503, detail={"code": "GATEWAY_UNAVAILABLE", "gateway": gateway})

    payload = {
        "gateway": gateway,
        "amount": amount_number,
        "currency": currency,
        "customer_email": email,
        "reference": body.get("reference"),
        "customer_name": current_user.get("name") or current_user.get("preferred_username"),
        "customer_phone": body.get("customer_phone"),
        "metadata": {"pricing": pricing},
    }
    result = await call("POST", f"{PAYMENTS_BASE}/checkout", creds.credentials, json=payload)
    if isinstance(result, dict):
        result["pricing"] = pricing
    return result


@router.get("/exchange/rates")
async def exchange_rates(limit: int = Query(default=100, ge=1, le=500), creds: HTTPAuthorizationCredentials = Depends(bearer)):
    await user(creds)
    return await call("GET", f"{EXCHANGE_BASE}/api/v1/rates?limit={limit}", creds.credentials)


@router.get("/rate/{frm}/{to}")
async def rate(frm: str, to: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    await user(creds)
    return await call("GET", f"{EXCHANGE_BASE}/api/v1/rates/{quote(frm.upper(), safe='')}/{quote(to.upper(), safe='')}", creds.credentials)


@router.post("/exchange/quote")
async def exchange_quote(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    await user(creds)
    from_currency = str(body.get("from_currency", "")).strip().upper()
    to_currency = str(body.get("to_currency", "")).strip().upper()
    amount = body.get("amount")
    if not from_currency or not to_currency or amount is None:
        raise HTTPException(status_code=422, detail="from_currency, to_currency and amount are required")
    try:
        amount_number = float(amount)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail="amount must be numeric") from e
    if not math.isfinite(amount_number) or amount_number <= 0:
        raise HTTPException(status_code=422, detail="amount must be greater than zero")
    rate_data = await call("GET", f"{EXCHANGE_BASE}/api/v1/rates/{quote(from_currency, safe='')}/{quote(to_currency, safe='')}", creds.credentials)
    try:
        rate_value = float(rate_data["rate"])
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=502, detail="Exchange service returned an invalid rate") from e
    if not math.isfinite(rate_value) or rate_value <= 0:
        raise HTTPException(status_code=502, detail="Exchange service returned an invalid rate")
    return {"from_currency": from_currency, "to_currency": to_currency, "amount": amount_number, "rate": rate_value, "converted_amount": round(amount_number * rate_value, 2), "source": rate_data.get("source"), "fetched_at": rate_data.get("fetched_at")}


@router.post("/exchange/convert")
async def exchange_convert(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    current_user = await user(creds)
    from_currency = str(body.get("from_currency", "")).strip().upper()
    to_currency = str(body.get("to_currency", "")).strip().upper()
    amount = body.get("amount")
    if not from_currency or not to_currency or amount is None:
        raise HTTPException(status_code=422, detail="from_currency, to_currency and amount are required")
    try:
        amount_number = float(amount)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail="amount must be numeric") from e
    if not math.isfinite(amount_number) or amount_number <= 0:
        raise HTTPException(status_code=422, detail="amount must be greater than zero")
    payload = {"from_currency": from_currency, "to_currency": to_currency, "amount": amount_number, "user_id": current_user.get("sub") or current_user.get("id")}
    return await call("POST", f"{EXCHANGE_BASE}/api/v1/convert", creds.credentials, json=payload)
