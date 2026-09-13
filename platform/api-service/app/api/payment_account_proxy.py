"""Unified-API facade for public and admin payment-account registry."""

import httpx
from app.core.security import verify_token
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter()
bearer = HTTPBearer()
PAYMENT = "http://payment-service.shopno-payments.svc.cluster.local:80"


async def token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc
    return creds.credentials


async def proxy(method: str, path: str, access_token: str | None = None, **kwargs):
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(method, f"{PAYMENT}{path}", headers=headers, **kwargs)
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


@router.get("/payment-accounts/public")
async def public_payment_accounts():
    return await proxy("GET", "/api/v1/payment-accounts/public")


@router.get("/admin/payment-accounts")
async def admin_payment_accounts(access_token: str = Depends(token)):
    return await proxy("GET", "/api/v1/payment-accounts/admin", access_token)


@router.post("/admin/payment-accounts", status_code=201)
async def admin_payment_account_create(body: dict, access_token: str = Depends(token)):
    return await proxy("POST", "/api/v1/payment-accounts/admin", access_token, json=body)


@router.patch("/admin/payment-accounts/{account_id}")
async def admin_payment_account_update(account_id: str, body: dict, access_token: str = Depends(token)):
    return await proxy("PATCH", f"/api/v1/payment-accounts/admin/{account_id}", access_token, json=body)


@router.delete("/admin/payment-accounts/{account_id}")
async def admin_payment_account_delete(account_id: str, access_token: str = Depends(token)):
    return await proxy("DELETE", f"/api/v1/payment-accounts/admin/{account_id}", access_token)
