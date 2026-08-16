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
    try:
        await verify_token(creds.credentials)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from e

    return await call(
        "GET",
        "http://oauth-service.shopno-identity.svc.cluster.local:80/api/v1/users/me",
        creds.credentials,
    )


@router.get("/users/me")
async def users_me(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        "http://oauth-service.shopno-identity.svc.cluster.local:80/api/v1/users/me",
        creds.credentials,
    )


@router.get("/wallets")
async def wallets(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        await verify_token(creds.credentials)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from e

    return await call(
        "GET",
        "http://billing-engine.shopno-payments.svc.cluster.local:80/api/v1/wallets",
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


@router.get("/subscription")
async def subscription(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call(
        "GET",
        "http://billing-engine.shopno-payments.svc.cluster.local:80/api/v1/subscriptions/me",
        creds.credentials,
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
