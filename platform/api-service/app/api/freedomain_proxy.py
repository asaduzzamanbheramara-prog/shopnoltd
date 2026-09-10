"""Unified browser facade for free Shopnoltd tenant domains."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()
FREE_DOMAIN = "http://freedomain-service.shopno-platform.svc.cluster.local:8080"


async def token(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc
    return creds.credentials


async def proxy(request: Request, path: str, raw_token: str):
    headers = {"Accept": "application/json", "Authorization": f"Bearer {raw_token}"}
    if request.headers.get("content-type"):
        headers["Content-Type"] = request.headers["content-type"]
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            upstream = await client.request(
                request.method,
                f"{FREE_DOMAIN}{path}",
                headers=headers,
                params=dict(request.query_params),
                content=await request.body(),
            )
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Free-domain service unavailable") from exc
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=upstream.headers.get("content-type", "application/json").split(";", 1)[0])


@router.api_route("/free-domains", methods=["GET", "POST"])
async def collection(request: Request, raw_token: str = Depends(token)):
    return await proxy(request, "/api/v1/domains", raw_token)


@router.api_route("/free-domains/me", methods=["GET"])
async def mine(request: Request, raw_token: str = Depends(token)):
    return await proxy(request, "/api/v1/domains/me", raw_token)


@router.api_route("/free-domains/check-availability", methods=["GET"])
async def availability(request: Request, raw_token: str = Depends(token)):
    return await proxy(request, "/api/v1/domains/check-availability", raw_token)


@router.api_route("/free-domains/{dom_id}", methods=["DELETE"])
async def remove(request: Request, dom_id: str, raw_token: str = Depends(token)):
    return await proxy(request, f"/api/v1/domains/{dom_id}", raw_token)
