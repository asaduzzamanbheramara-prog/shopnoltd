"""Unified admin database capability catalog.

This endpoint is discovery only. It never executes SQL and never grants a
capability that an owning service has not declared and enforced itself.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token
from app.database_control_plane.registry import catalog

router = APIRouter(prefix="/admin/database", tags=["admin-database-control-plane"])
bearer = HTTPBearer(auto_error=True)


async def require_platform_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    token = await verify_token(credentials.credentials)
    roles = set(token.get("roles", []))
    if "platform_admin" not in roles:
        raise HTTPException(403, "platform_admin required")
    return token


@router.get("/catalog")
async def database_catalog(_: dict = Depends(require_platform_admin)):
    return {
        "version": 1,
        "policy": "capability-driven",
        "sql_endpoint": False,
        "databases": catalog(),
    }
