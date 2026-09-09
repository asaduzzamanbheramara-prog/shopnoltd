"""Browser-safe admin data facade.

The portal uses the unified API origin. This router exposes service-owned admin
operations without creating a generic cross-service SQL interface or bypassing
service authorization.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()
PAYMENT = "http://payment-service.shopno-payments.svc.cluster.local:80"
SOCIAL = "http://social-service.shopno-platform.svc.cluster.local:80"


async def current_token(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from exc
    return creds.credentials


async def proxy(request: Request, base: str, path: str, token: str, *, content: bytes | None = None):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if request.headers.get("content-type"):
        headers["Content-Type"] = request.headers["content-type"]
    params = dict(request.query_params)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            upstream = await client.request(
                request.method,
                f"{base}{path}",
                headers=headers,
                params=params,
                content=content if content is not None else await request.body(),
            )
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(status_code=503, detail="Admin data service unavailable") from exc
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json").split(";", 1)[0],
    )


@router.api_route("/admin/tables", methods=["GET"])
async def admin_tables(request: Request, token: str = Depends(current_token)):
    return await proxy(request, PAYMENT, "/api/v1/admin/tables", token)


@router.api_route("/admin/tables/{name}", methods=["GET"])
async def admin_table(request: Request, name: str, token: str = Depends(current_token)):
    return await proxy(request, PAYMENT, f"/api/v1/admin/tables/{name}", token)


@router.api_route("/admin/tables/{name}/analysis", methods=["GET"])
async def admin_table_analysis(request: Request, name: str, token: str = Depends(current_token)):
    return await proxy(request, PAYMENT, f"/api/v1/admin/tables/{name}/analysis", token)


@router.api_route("/admin/tables/{name}/export", methods=["GET"])
async def admin_table_export(request: Request, name: str, token: str = Depends(current_token)):
    return await proxy(request, PAYMENT, f"/api/v1/admin/tables/{name}/export", token)


@router.api_route("/admin/blog-data/schema", methods=["GET"])
async def admin_blog_schema(request: Request, token: str = Depends(current_token)):
    return await proxy(request, SOCIAL, "/api/v1/admin/blog-data/schema", token)


@router.api_route("/admin/blog-data/analysis", methods=["GET"])
async def admin_blog_analysis(request: Request, token: str = Depends(current_token)):
    return await proxy(request, SOCIAL, "/api/v1/admin/blog-data/analysis", token)


@router.api_route("/admin/blog-data/check", methods=["GET"])
async def admin_blog_check(request: Request, token: str = Depends(current_token)):
    return await proxy(request, SOCIAL, "/api/v1/admin/blog-data/check", token)


@router.api_route("/admin/blog-data/rows", methods=["POST"])
async def admin_blog_create(request: Request, token: str = Depends(current_token)):
    return await proxy(request, SOCIAL, "/api/v1/admin/blog-data/rows", token)


@router.api_route("/admin/blog-data/rows/{record_id}", methods=["PUT", "DELETE"])
async def admin_blog_row(request: Request, record_id: str, token: str = Depends(current_token)):
    return await proxy(request, SOCIAL, f"/api/v1/admin/blog-data/rows/{record_id}", token)


@router.api_route("/admin/blog-data/rows/{record_id}/publish", methods=["POST"])
async def admin_blog_publish(request: Request, record_id: str, token: str = Depends(current_token)):
    return await proxy(request, SOCIAL, f"/api/v1/admin/blog-data/rows/{record_id}/publish", token)


@router.api_route("/admin/blog-data/export", methods=["GET"])
async def admin_blog_export(request: Request, token: str = Depends(current_token)):
    return await proxy(request, SOCIAL, "/api/v1/admin/blog-data/export", token)


@router.api_route("/admin/blog-data/import/preview", methods=["POST"])
async def admin_blog_import_preview(request: Request, token: str = Depends(current_token)):
    return await proxy(request, SOCIAL, "/api/v1/admin/blog-data/import/preview", token)


@router.api_route("/admin/blog-data/import", methods=["POST"])
async def admin_blog_import(request: Request, token: str = Depends(current_token)):
    return await proxy(request, SOCIAL, "/api/v1/admin/blog-data/import", token)
