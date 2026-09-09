"""Versioned REST facade that aggregates downstream services."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import Response

from app.core.financial_registry import GATEWAY_REGISTRY, PAYOUT_PROVIDERS
from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()
SOCIAL = "http://social-service.shopno-platform.svc.cluster.local:80"
BILLING = "http://billing-engine.shopno-payments.svc.cluster.local:80"
EXCHANGE = "http://exchange-service.shopno-payments.svc.cluster.local:80"
PAYMENT = "http://payment-service.shopno-payments.svc.cluster.local:80"

async def user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try: return await verify_token(creds.credentials)
    except Exception as e: raise HTTPException(status_code=401, detail="Invalid authentication token") from e

async def call(method: str, url: str, user_token: str, **kw):
    headers = {"Authorization": f"Bearer {user_token}"}
    try:
        async with httpx.AsyncClient(timeout=10) as c: r = await c.request(method, url, headers=headers, **kw)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
        raise HTTPException(status_code=503, detail="Downstream service unavailable") from e
    if r.status_code >= 400:
        detail = r.text
        try: detail = r.json()
        except Exception: pass
        raise HTTPException(status_code=r.status_code, detail=detail)
    return r.json() if r.text else None

async def public_call(method: str, url: str, **kw):
    try:
        async with httpx.AsyncClient(timeout=10) as c: r = await c.request(method, url, **kw)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
        raise HTTPException(status_code=503, detail="Downstream service unavailable") from e
    if r.status_code >= 400:
        detail = r.text
        try: detail = r.json()
        except Exception: pass
        raise HTTPException(status_code=r.status_code, detail=detail)
    return r.json() if r.text else None

@router.get("/me")
async def me(creds: HTTPAuthorizationCredentials = Depends(bearer)): return await user(creds)

@router.get("/users/me")
async def users_me(creds: HTTPAuthorizationCredentials = Depends(bearer)): return await user(creds)

@router.get("/wallets")
async def wallets(creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("GET", f"{PAYMENT}/api/v1/wallets", creds.credentials)

@router.get("/wallets/{currency}")
async def payment_wallet(currency: str, creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("GET", f"{PAYMENT}/api/v1/wallets/{currency.upper()}", creds.credentials)

@router.get("/wallets/{currency}/ledger")
async def payment_wallet_ledger(currency: str, limit: int = Query(50, ge=1, le=200), creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", f"{PAYMENT}/api/v1/wallets/{currency.upper()}/ledger", creds.credentials, params={"limit": limit})

@router.get("/wallet")
async def wallet(creds: HTTPAuthorizationCredentials = Depends(bearer), currency: str = Query("BDT")): return await call("GET", f"{PAYMENT}/api/v1/wallets/{currency.upper()}", creds.credentials)

@router.get("/wallet/ledger")
async def wallet_ledger(creds: HTTPAuthorizationCredentials = Depends(bearer), currency: str = Query("BDT"), limit: int = Query(50, ge=1, le=200)):
    return await call("GET", f"{PAYMENT}/api/v1/wallets/{currency.upper()}/ledger", creds.credentials, params={"limit": limit})

@router.get("/transactions")
async def transactions(creds: HTTPAuthorizationCredentials = Depends(bearer), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    return await call("GET", f"{PAYMENT}/api/v1/transactions", creds.credentials, params={"limit": limit, "offset": offset})

@router.get("/billing/gateways")
async def billing_gateways(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    methods = await call("GET", f"{PAYMENT}/api/v1/methods", creds.credentials)
    items = methods.get("methods", []) if isinstance(methods, dict) else []
    gateways = []
    for item in items:
        method = item.get("id") or item.get("name")
        meta = GATEWAY_REGISTRY.get(method, {})
        enabled = bool(item.get("enabled", True))
        native = meta.get("integration") == "native"
        gateways.append({
            "name": method, "id": method,
            "display_name": item.get("display_name") or meta.get("name") or str(method).replace("_", " ").title(),
            "enabled": enabled, "available": enabled and native, "live": enabled and native,
            "integration": meta.get("integration", "unknown"),
            "capabilities": meta.get("capabilities", []),
            "currencies": item.get("currencies") or meta.get("currencies", []),
            "payment_methods": meta.get("payment_methods", []),
            "notes": meta.get("notes"),
        })
    return {"gateways": gateways, "payout_providers": PAYOUT_PROVIDERS}

@router.get("/currencies")
async def currencies(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    methods = await call("GET", f"{PAYMENT}/api/v1/methods", creds.credentials)
    items = methods.get("methods", []) if isinstance(methods, dict) else []
    available = sorted({str(c).upper() for item in items if item.get("enabled", True) for c in item.get("currencies", [])})
    return {"currencies": available}

@router.get("/methods")
async def payment_methods(creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("GET", f"{PAYMENT}/api/v1/methods", creds.credentials)

@router.post("/deposits")
async def payment_deposit(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("POST", f"{PAYMENT}/api/v1/deposits", creds.credentials, json=body)

@router.get("/deposits/{tx_id}")
async def payment_deposit_detail(tx_id: str, creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("GET", f"{PAYMENT}/api/v1/deposits/{tx_id}", creds.credentials)

@router.post("/withdrawals")
async def payment_withdrawal(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("POST", f"{PAYMENT}/api/v1/withdrawals", creds.credentials, json=body)

@router.post("/transfers")
async def payment_transfer(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("POST", f"{PAYMENT}/api/v1/transfers", creds.credentials, json=body)

@router.get("/exchanges/rate")
async def payment_exchange_rate(from_currency: str, to_currency: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", f"{PAYMENT}/api/v1/exchanges/rate", creds.credentials, params={"from_currency": from_currency.upper(), "to_currency": to_currency.upper()})

@router.post("/exchanges/convert")
async def payment_exchange_convert(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    payload = dict(body); payload["from_currency"] = str(payload.get("from_currency", "")).upper(); payload["to_currency"] = str(payload.get("to_currency", "")).upper()
    if not payload["from_currency"] or not payload["to_currency"] or payload.get("amount") is None: raise HTTPException(status_code=422, detail="from_currency, to_currency and amount are required")
    if not payload.get("idempotency_key"): raise HTTPException(status_code=422, detail="idempotency_key is required")
    return await call("POST", f"{PAYMENT}/api/v1/exchanges/convert", creds.credentials, json=payload)

@router.get("/blog")
async def blog(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)): return await public_call("GET", f"{SOCIAL}/api/v1/blog", params={"limit": limit, "offset": offset})

@router.get("/blog/admin")
async def blog_admin(creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("GET", f"{SOCIAL}/api/v1/blog/admin", creds.credentials)

@router.get("/blog/{slug}")
async def blog_post(slug: str): return await public_call("GET", f"{SOCIAL}/api/v1/blog/{slug}")

@router.post("/blog")
async def blog_create(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("POST", f"{SOCIAL}/api/v1/blog", creds.credentials, json=body)

@router.put("/blog/{post_id}")
async def blog_update(post_id: str, body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("PUT", f"{SOCIAL}/api/v1/blog/{post_id}", creds.credentials, json=body)

@router.delete("/blog/{post_id}")
async def blog_delete(post_id: str, creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("DELETE", f"{SOCIAL}/api/v1/blog/{post_id}", creds.credentials)

@router.post("/webhook/moneybag/ipn")
async def moneybag_webhook(request: Request):
    body = await request.body(); headers = {key: value for key, value in request.headers.items() if key.lower().startswith("x-webhook-")}
    try:
        async with httpx.AsyncClient(timeout=20) as client: response = await client.post(f"{PAYMENT}/api/v1/webhooks/moneybag", content=body, headers=headers)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc: raise HTTPException(status_code=503, detail="Payment webhook service unavailable") from exc
    return Response(content=response.content, status_code=response.status_code, media_type=response.headers.get("content-type", "application/json").split(";", 1)[0])

@router.get("/feed")
async def feed(creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("GET", f"{SOCIAL}/api/v1/feed/me", creds.credentials)

@router.get("/conversations")
async def conversations(creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("GET", "http://messaging-service.shopno-platform.svc.cluster.local:80/api/v1/conversations", creds.credentials)

@router.get("/notifications")
async def notifications(creds: HTTPAuthorizationCredentials = Depends(bearer)): return await call("GET", "http://notification-service.shopno-platform.svc.cluster.local:80/api/v1/notifications/me", creds.credentials)

@router.post("/billing/checkout")
async def billing_checkout(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    current_user = await user(creds); email = current_user.get("email")
    if not email: raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")
    amount, currency = body.get("amount"), body.get("currency"); gateway = body.get("gateway", "stripe")
    if amount is None or not currency: raise HTTPException(status_code=422, detail="amount and currency are required")
    payload = {"gateway": gateway, "amount": amount, "currency": currency.upper(), "customer_email": email, "reference": body.get("reference"), "customer_name": current_user.get("name") or current_user.get("preferred_username"), "customer_phone": body.get("customer_phone")}
    return await call("POST", f"{BILLING}/checkout", creds.credentials, json=payload)

@router.get("/rate/{frm}/{to}")
async def rate(frm: str, to: str, creds: HTTPAuthorizationCredentials = Depends(bearer)): return await payment_exchange_rate(frm, to, creds)

@router.post("/exchange/convert")
async def exchange_convert(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)): return await payment_exchange_convert(body, creds)
