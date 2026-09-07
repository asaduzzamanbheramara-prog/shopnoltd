"""Versioned REST facade that aggregates downstream services.

The web portal talks only to this facade.  Downstream service URLs remain
internal implementation details so the public financial API can evolve
without coupling the browser to individual services.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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


@router.get("/me")
async def me(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await user(creds)


@router.get("/users/me")
async def users_me(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await user(creds)


@router.get("/financial/capabilities")
async def financial_capabilities(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    """Return the currently available financial capabilities.

    Gateway/currency information comes from the billing registry at runtime;
    the browser must not maintain its own gateway compatibility matrix.
    """
    await user(creds)
    gateways_response = await call("GET", f"{PAYMENTS_BASE}/gateways", creds.credentials)
    gateways = gateways_response.get("gateways", []) if isinstance(gateways_response, dict) else []

    currencies = sorted(
        {
            currency.upper()
            for gateway in gateways
            for currency in gateway.get("currencies", [])
            if isinstance(currency, str)
            and currency.strip()
            and "and more" not in currency.lower()
        }
    )

    return {
        "version": 1,
        "currencies": currencies,
        "gateways": gateways,
    }


@router.get("/wallet")
async def wallet(
    currency: str | None = Query(default=None),
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")

    query = f"?currency={currency.upper()}" if currency else ""
    return await call("GET", f"{PAYMENTS_BASE}/wallet/{email}{query}", creds.credentials)


@router.get("/wallet/{currency}")
async def wallet_by_currency(currency: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await wallet(currency=currency, creds=creds)


@router.get("/wallet/ledger")
async def wallet_ledger(
    currency: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")

    params = [f"limit={limit}"]
    if currency:
        params.append(f"currency={currency.upper()}")
    return await call(
        "GET",
        f"{PAYMENTS_BASE}/wallet/{email}/ledger?{'&'.join(params)}",
        creds.credentials,
    )


@router.get("/transactions")
async def transactions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")

    return await call(
        "GET",
        f"{PAYMENTS_BASE}/transactions/{email}?limit={limit}&offset={offset}",
        creds.credentials,
    )


@router.get("/feed")
async def feed(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        "http://social-service.shopno-platform.svc.cluster.local:80/api/v1/feed/me",
        creds.credentials,
    )


@router.get("/conversations")
async def conversations(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        "http://messaging-service.shopno-platform.svc.cluster.local:80/api/v1/conversations",
        creds.credentials,
    )


@router.get("/notifications")
async def notifications(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        "http://notification-service.shopno-platform.svc.cluster.local:80/api/v1/notifications/me",
        creds.credentials,
    )


@router.get("/billing/gateways")
async def billing_gateways(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    await user(creds)
    return await call("GET", f"{PAYMENTS_BASE}/gateways", creds.credentials)


@router.post("/billing/checkout")
async def billing_checkout(
    body: dict,
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")

    amount = body.get("amount")
    currency = str(body.get("currency") or "").upper()
    gateway = str(body.get("gateway") or "stripe").lower()

    if amount is None or not currency:
        raise HTTPException(status_code=422, detail="amount and currency are required")

    # Validate the gateway/currency pair against the live registry.  Entries
    # such as "and more" represent provider wildcards and are intentionally
    # not treated as exhaustive lists.
    capability = await call("GET", f"{PAYMENTS_BASE}/gateways", creds.credentials)
    gateway_row = next(
        (g for g in capability.get("gateways", []) if str(g.get("name", "")).lower() == gateway),
        None,
    )
    if gateway_row is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "GATEWAY_UNSUPPORTED", "gateway": gateway},
        )
    supported = {
        str(c).upper()
        for c in gateway_row.get("currencies", [])
        if isinstance(c, str) and "and more" not in c.lower()
    }
    if supported and currency not in supported:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "GATEWAY_CURRENCY_UNSUPPORTED",
                "gateway": gateway,
                "currency": currency,
                "supported_currencies": sorted(supported),
            },
        )
    if gateway_row.get("live") is False:
        raise HTTPException(
            status_code=503,
            detail={"code": "GATEWAY_UNAVAILABLE", "gateway": gateway},
        )

    payload = {
        "gateway": gateway,
        "amount": amount,
        "currency": currency,
        "customer_email": email,
        "reference": body.get("reference"),
        "customer_name": current_user.get("name") or current_user.get("preferred_username"),
        "customer_phone": body.get("customer_phone"),
    }
    return await call("POST", f"{PAYMENTS_BASE}/checkout", creds.credentials, json=payload)


@router.get("/exchange/rates")
async def exchange_rates(
    limit: int = Query(default=100, ge=1, le=500),
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    await user(creds)
    return await call("GET", f"{EXCHANGE_BASE}/api/v1/rates?limit={limit}", creds.credentials)


@router.get("/rate/{frm}/{to}")
async def rate(frm: str, to: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    await user(creds)
    return await call(
        "GET",
        f"{EXCHANGE_BASE}/api/v1/rates/{frm.upper()}/{to.upper()}",
        creds.credentials,
    )


@router.post("/exchange/quote")
async def exchange_quote(
    body: dict,
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    await user(creds)
    from_currency = str(body.get("from_currency", "")).upper()
    to_currency = str(body.get("to_currency", "")).upper()
    amount = body.get("amount")
    if not from_currency or not to_currency or amount is None:
        raise HTTPException(status_code=422, detail="from_currency, to_currency and amount are required")
    rate_data = await call(
        "GET",
        f"{EXCHANGE_BASE}/api/v1/rates/{from_currency}/{to_currency}",
        creds.credentials,
    )
    rate_value = float(rate_data["rate"])
    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "amount": amount,
        "rate": rate_value,
        "converted_amount": float(amount) * rate_value,
        "source": rate_data.get("source"),
        "fetched_at": rate_data.get("fetched_at"),
    }


@router.post("/exchange/convert")
async def exchange_convert(
    body: dict,
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    current_user = await user(creds)
    from_currency = str(body.get("from_currency", "")).upper()
    to_currency = str(body.get("to_currency", "")).upper()
    amount = body.get("amount")
    if not from_currency or not to_currency or amount is None:
        raise HTTPException(status_code=422, detail="from_currency, to_currency and amount are required")

    payload = {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "amount": amount,
        "user_id": current_user.get("sub") or current_user.get("id"),
    }
    return await call(
        "POST",
        f"{EXCHANGE_BASE}/api/v1/convert",
        creds.credentials,
        json=payload,
    )
