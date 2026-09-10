"""Unified browser facade for Shopnoltd AI services.

The browser talks only to api.shopnoltd.dpdns.org. Provider credentials and
AI service topology remain server-side; the user's Keycloak bearer token is
forwarded to the owning AI service for its normal authorization checks.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()
AI = "http://ai-platform.shopno-platform.svc.cluster.local:80"


async def raw_token(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc
    return creds.credentials


async def proxy(request: Request, upstream_path: str, token: str):
    headers = {"Accept": request.headers.get("accept", "application/json"), "Authorization": f"Bearer {token}"}
    if request.headers.get("content-type"):
        headers["Content-Type"] = request.headers["content-type"]
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            upstream = await client.request(request.method, f"{AI}{upstream_path}", headers=headers, params=dict(request.query_params), content=await request.body())
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "AI service unavailable") from exc
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=upstream.headers.get("content-type", "application/json").split(";", 1)[0])


@router.api_route("/ai/inference", methods=["POST"])
async def inference(request: Request, token: str = Depends(raw_token)):
    return await proxy(request, "/api/v1/inference", token)


@router.api_route("/ai/inference/models", methods=["GET"])
async def inference_models(request: Request, token: str = Depends(raw_token)):
    return await proxy(request, "/api/v1/inference/models", token)


@router.api_route("/ai/providers", methods=["GET", "POST"])
@router.api_route("/ai/providers/{provider_id}", methods=["GET", "PATCH", "DELETE"])
async def providers(request: Request, provider_id: str | None = None, token: str = Depends(raw_token)):
    return await proxy(request, "/api/ai/providers" + (f"/{provider_id}" if provider_id else ""), token)


@router.api_route("/ai/models", methods=["GET", "POST"])
@router.api_route("/ai/models/{model_id}", methods=["GET", "PATCH", "DELETE"])
async def models(request: Request, model_id: str | None = None, token: str = Depends(raw_token)):
    return await proxy(request, "/api/ai/models" + (f"/{model_id}" if model_id else ""), token)


@router.api_route("/ai/embeddings/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def embeddings(request: Request, path: str, token: str = Depends(raw_token)):
    return await proxy(request, f"/api/v1/embeddings/{path}", token)


@router.api_route("/ai/documents/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def documents(request: Request, path: str, token: str = Depends(raw_token)):
    return await proxy(request, f"/api/v1/documents/{path}", token)


@router.api_route("/ai/agents/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def agents(request: Request, path: str, token: str = Depends(raw_token)):
    return await proxy(request, f"/api/v1/agents/{path}", token)
