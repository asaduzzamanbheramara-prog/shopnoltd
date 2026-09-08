"""Unified blog facade. Browser clients stay on the Shopnoltd API origin."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer(auto_error=False)
SOCIAL = "http://social-service.shopno-platform.svc.cluster.local:80"


async def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if creds is None:
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        return creds, await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc


async def call(method: str, path: str, token: str | None = None, **kwargs):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(method, f"{SOCIAL}{path}", headers=headers, **kwargs)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Blog service unavailable") from exc
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise HTTPException(response.status_code, detail)
    return response.json() if response.text else None


@router.get("/blog")
async def public_blog():
    return await call("GET", "/api/v1/blog")


@router.get("/blog/{slug}")
async def get_blog_post(slug: str):
    return await call("GET", f"/api/v1/blog/{slug}")


@router.get("/blog/mine")
async def my_blog(auth=Depends(current_user)):
    creds, _ = auth
    return await call("GET", "/api/v1/blog/mine", creds.credentials)


@router.get("/blog/admin")
async def admin_blog(auth=Depends(current_user)):
    creds, _ = auth
    return await call("GET", "/api/v1/blog/admin", creds.credentials)


@router.post("/blog")
async def create_blog_post(body: dict, auth=Depends(current_user)):
    creds, _ = auth
    return await call("POST", "/api/v1/blog", creds.credentials, json=body)


@router.put("/blog/{post_id}")
async def update_blog_post(post_id: str, body: dict, auth=Depends(current_user)):
    creds, _ = auth
    return await call("PUT", f"/api/v1/blog/{post_id}", creds.credentials, json=body)


@router.delete("/blog/{post_id}")
async def delete_blog_post(post_id: str, auth=Depends(current_user)):
    creds, _ = auth
    return await call("DELETE", f"/api/v1/blog/{post_id}", creds.credentials)
