"""Unified-API facade for direct-number payment flows."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()
PAYMENT = "http://payment-service.shopno-payments.svc.cluster.local:80"


async def token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc
    return creds.credentials


async def proxy(method: str, path: str, access_token: str, **kwargs):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(method, f"{PAYMENT}{path}", headers={"Authorization": f"Bearer {access_token}"}, **kwargs)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Payment service unavailable") from exc
    detail = response.text
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            pass
        raise HTTPException(response.status_code, detail)
    return response.json() if response.text else None


@router.get("/direct-payments/accounts")
async def direct_payment_accounts(provider: str | None = None, access_token: str = Depends(token)):
    return await proxy("GET", "/api/v1/direct-payments/accounts", access_token, params={"provider": provider} if provider else None)


@router.post("/direct-payments/intents", status_code=201)
async def direct_payment_intent(body: dict, access_token: str = Depends(token)):
    return await proxy("POST", "/api/v1/direct-payments/intents", access_token, json=body)


@router.get("/direct-payments/intents/{intent_id}")
async def direct_payment_intent_detail(intent_id: str, access_token: str = Depends(token)):
    return await proxy("GET", f"/api/v1/direct-payments/intents/{intent_id}", access_token)


@router.post("/direct-payments/intents/{intent_id}/submit", status_code=201)
async def direct_payment_submit(intent_id: str, body: dict, access_token: str = Depends(token)):
    return await proxy("POST", f"/api/v1/direct-payments/intents/{intent_id}/submit", access_token, json=body)
