"""Authenticated blog collection routes kept ahead of public slug routing."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter()
bearer = HTTPBearer(auto_error=False)
SOCIAL = "http://social-service.shopno-platform.svc.cluster.local:80"


async def current_token(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if creds is None:
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return creds.credentials


async def call(path: str, token: str):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{SOCIAL}{path}", headers={"Authorization": f"Bearer {token}"})
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Blog service unavailable") from exc
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise HTTPException(response.status_code, detail)
    return response.json() if response.text else None


@router.get("/blog/mine")
async def my_blog(token: str = Depends(current_token)):
    return await call("/api/v1/blog/mine", token)


@router.get("/blog/admin")
async def admin_blog(token: str = Depends(current_token)):
    return await call("/api/v1/blog/admin", token)
