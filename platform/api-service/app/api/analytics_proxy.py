"""Privacy-safe public collection and protected analytics reporting facade."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer(auto_error=False)
ANALYTICS = "http://analytics-service.shopno-platform.svc.cluster.local:80"


async def _forward(method: str, path: str, *, token: str | None = None, json_body=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.request(method, f"{ANALYTICS}{path}", headers=headers, json=json_body)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Analytics service unavailable") from exc
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise HTTPException(response.status_code, detail)
    return response.json() if response.text else None


@router.post("/analytics/collect", status_code=202)
async def collect(request: Request):
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(400, "Invalid analytics payload") from exc
    cf_country = request.headers.get("cf-ipcountry")
    if cf_country and isinstance(body.get("properties"), dict):
        body["properties"].setdefault("country", cf_country.upper())
    return await _forward("POST", "/api/v1/events/public", json_body=body)


@router.get("/analytics/reports/visitors")
async def visitors(days: int = 30, limit: int = 20, creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if creds is None:
        raise HTTPException(401, "Authentication required")
    user = await verify_token(creds.credentials)
    return await _forward(
        "GET",
        f"/api/v1/reports/visitors?days={max(1, min(days, 365))}&limit={max(1, min(limit, 100))}",
        token=creds.credentials,
    )
