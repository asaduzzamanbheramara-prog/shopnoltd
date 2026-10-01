"""Public API facade for the Shopnoltd advertising service.

The browser talks only to api.shopnoltd.dpdns.org. The ad-service remains
cluster-internal; the user's validated Keycloak bearer token is forwarded to
its normal authorization checks.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()


async def raw_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> str:
    try:
        await verify_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc
    return credentials.credentials


@router.api_route(
    "/ads/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def ads_proxy(
    request: Request,
    path: str,
    token: str = Depends(raw_token),
):
    headers = {
        "Accept": request.headers.get("accept", "application/json"),
        "Authorization": f"Bearer {token}",
    }
    if request.headers.get("content-type"):
        headers["Content-Type"] = request.headers["content-type"]
    upstream_url = f"http://ad-service.shopno-platform.svc.cluster.local:8080/v1/ads/{path}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            upstream = await client.request(
                request.method,
                upstream_url,
                headers=headers,
                params=request.query_params,
                content=await request.body(),
            )
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Advertising service unavailable") from exc

    media_type = upstream.headers.get("content-type", "application/json").split(";", 1)[0]
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=media_type,
    )
