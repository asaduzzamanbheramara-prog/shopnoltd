"""Versioned REST facade that aggregates downstream services."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()

SOCIAL = "http://social-service.shopno-platform.svc.cluster.local:80"
BILLING = "http://billing-engine.shopno-payments.svc.cluster.local:80"
EXCHANGE = "http://exchange-service.shopno-payments.svc.cluster.local:80"


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


async def public_call(method: str, url: str, **kw):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.request(method, url, **kw)
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


@router.get("/wallet")
async def wallet(creds: HTTPAuthorizationCredentials = Depends(bearer), currency: str = Query("BDT")):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")
    return await call("GET", f"{BILLING}/wallet/{email}", creds.credentials, params={"currency": currency.upper()})


@router.get("/wallet/ledger")
async def wallet_ledger(creds: HTTPAuthorizationCredentials = Depends(bearer), currency: str = Query("BDT")):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")
    return await call("GET", f"{BILLING}/wallet/{email}/ledger", creds.credentials, params={"currency": currency.upper()})


@router.get("/transactions")
async def transactions(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")
    return await call("GET", f"{BILLING}/transactions/{email}", creds.credentials)


@router.get("/blog")
async def blog(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    return await public_call("GET", f"{SOCIAL}/api/v1/blog", params={"limit": limit, "offset": offset})


@router.get("/blog/{slug}")
async def blog_post(slug: str):
    return await public_call("GET", f"{SOCIAL}/api/v1/blog/{slug}")


@router.get("/blog/admin")
async def blog_admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", f"{SOCIAL}/api/v1/blog/admin", creds.credentials)


@router.post("/blog")
async def blog_create(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("POST", f"{SOCIAL}/api/v1/blog", creds.credentials, json=body)


@router.put("/blog/{post_id}")
async def blog_update(post_id: str, body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("PUT", f"{SOCIAL}/api/v1/blog/{post_id}", creds.credentials, json=body)


@router.delete("/blog/{post_id}")
async def blog_delete(post_id: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("DELETE", f"{SOCIAL}/api/v1/blog/{post_id}", creds.credentials)


@router.get("/feed")
async def feed(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", f"{SOCIAL}/api/v1/feed/me", creds.credentials)


@router.get("/conversations")
async def conversations(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", "http://messaging-service.shopno-platform.svc.cluster.local:80/api/v1/conversations", creds.credentials)


@router.get("/notifications")
async def notifications(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", "http://notification-service.shopno-platform.svc.cluster.local:80/api/v1/notifications/me", creds.credentials)


@router.get("/billing/gateways")
async def billing_gateways(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    await user(creds)
    return await call("GET", f"{BILLING}/gateways", creds.credentials)


@router.post("/billing/checkout")
async def billing_checkout(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    current_user = await user(creds)
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Authenticated user does not have an email address")
    amount = body.get("amount")
    currency = body.get("currency")
    gateway = body.get("gateway", "stripe")
    if amount is None or not currency:
        raise HTTPException(status_code=422, detail="amount and currency are required")
    payload = {
        "gateway": gateway,
        "amount": amount,
        "currency": currency.upper(),
        "customer_email": email,
        "reference": body.get("reference"),
        "customer_name": current_user.get("name") or current_user.get("preferred_username"),
        "customer_phone": body.get("customer_phone"),
    }
    return await call("POST", f"{BILLING}/checkout", creds.credentials, json=payload)


@router.get("/rate/{frm}/{to}")
async def rate(frm: str, to: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    await user(creds)
    return await call("GET", f"{EXCHANGE}/api/v1/rates/{frm.upper()}/{to.upper()}", creds.credentials)


@router.post("/exchange/convert")
async def exchange_convert(body: dict, creds: HTTPAuthorizationCredentials = Depends(bearer)):
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
    return await call("POST", f"{EXCHANGE}/api/v1/convert", creds.credentials, json=payload)
