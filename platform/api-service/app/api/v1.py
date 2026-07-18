"""Versioned REST facade that aggregates downstream services."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()


async def user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


async def call(method: str, url: str, user_token: str, **kw):
    headers = {"Authorization": f"Bearer {user_token}"}
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.request(method, url, headers=headers, **kw)
    if r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)
    return r.json() if r.text else None


@router.get("/me")
async def me(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        "http://oauth-service.shopno-identity.svc.cluster.local:8080/api/v1/users/me",
        creds.credentials,
    )


@router.get("/wallets")
async def wallets(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        "http://payment-service.shopno-payments.svc.cluster.local:8080/api/v1/wallets",
        creds.credentials,
    )


@router.get("/feed")
async def feed(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        "http://social-service.shopno-platform.svc.cluster.local:8080/api/v1/feed/me",
        creds.credentials,
    )


@router.get("/conversations")
async def conversations(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        "http://messaging-service.shopno-platform.svc.cluster.local:8080/api/v1/conversations",
        creds.credentials,
    )


@router.get("/notifications")
async def notifications(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        "http://notification-service.shopno-platform.svc.cluster.local:8080/api/v1/notifications/me",
        creds.credentials,
    )


@router.get("/subscription")
async def subscription(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        "http://billing-engine.shopno-payments.svc.cluster.local:8080/api/v1/subscriptions/me",
        creds.credentials,
    )


@router.get("/rate/{frm}/{to}")
async def rate(frm: str, to: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        f"http://exchange-service.shopno-payments.svc.cluster.local:8080/api/v1/rates/{frm}/{to}",
        creds.credentials,
    )
