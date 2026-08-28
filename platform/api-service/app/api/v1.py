"""Versioned REST facade that aggregates downstream services."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()


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
        raise HTTPException(
            status_code=503,
            detail="Downstream service unavailable",
        ) from e

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
async def wallet(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    current_user = await user(creds)

    email = current_user.get("email")
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Authenticated user does not have an email address",
        )

    return await call(
        "GET",
        f"http://billing-engine.shopno-payments.svc.cluster.local:80/wallet/{email}",
        creds.credentials,
    )


@router.get("/wallet/ledger")
async def wallet_ledger(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    current_user = await user(creds)

    email = current_user.get("email")
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Authenticated user does not have an email address",
        )

    return await call(
        "GET",
        f"http://billing-engine.shopno-payments.svc.cluster.local:80/wallet/{email}/ledger",
        creds.credentials,
    )


@router.get("/transactions")
async def transactions(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    current_user = await user(creds)

    email = current_user.get("email")
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Authenticated user does not have an email address",
        )

    return await call(
        "GET",
        f"http://billing-engine.shopno-payments.svc.cluster.local:80/transactions/{email}",
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
async def billing_gateways(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    await user(creds)

    return await call(
        "GET",
        "http://billing-engine.shopno-payments.svc.cluster.local:80/gateways",
        creds.credentials,
    )


@router.post("/billing/checkout")
async def billing_checkout(
    body: dict,
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    current_user = await user(creds)

    email = current_user.get("email")
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Authenticated user does not have an email address",
        )

    amount = body.get("amount")
    currency = body.get("currency")
    gateway = body.get("gateway", "stripe")

    if amount is None or not currency:
        raise HTTPException(
            status_code=422,
            detail="amount and currency are required",
        )

    payload = {
        "gateway": gateway,
        "amount": amount,
        "currency": currency.upper(),
        "customer_email": email,
        "reference": body.get("reference"),
        "customer_name": (current_user.get("name") or current_user.get("preferred_username")),
        "customer_phone": body.get("customer_phone"),
    }

    return await call(
        "POST",
        "http://billing-engine.shopno-payments.svc.cluster.local:80/checkout",
        creds.credentials,
        json=payload,
    )


@router.get("/rate/{frm}/{to}")
async def rate(frm: str, to: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        await verify_token(creds.credentials)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from e

    raise HTTPException(
        status_code=503,
        detail="Exchange service is not deployed",
    )
