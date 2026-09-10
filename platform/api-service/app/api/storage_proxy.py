"""Unified browser facade for authenticated storage mutations and reads."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()
STORAGE = "http://storage-service.shopno-platform.svc.cluster.local:80"


async def token(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc
    return creds.credentials


@router.api_route("/storage/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def storage(request: Request, path: str, raw_token: str = Depends(token)):
    headers = {"Accept": request.headers.get("accept", "application/json"), "Authorization": f"Bearer {raw_token}"}
    if request.headers.get("content-type"):
        headers["Content-Type"] = request.headers["content-type"]
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            upstream = await client.request(request.method, f"{STORAGE}/api/v1/{path}", headers=headers, params=dict(request.query_params), content=await request.body())
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Storage service unavailable") from exc
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=upstream.headers.get("content-type", "application/json").split(";", 1)[0])
