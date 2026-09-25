"""Unified admin database capability and live inventory control plane.

Discovery is read-only. Mutations remain capability-driven and service-owned.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token
from app.database_control_plane.discovery import reconcile_postgres
from app.database_control_plane.registry import catalog

router = APIRouter(prefix="/admin/database", tags=["admin-database-control-plane"])
bearer = HTTPBearer(auto_error=True)


async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    """Allow administrators to inspect the guarded control-plane catalog."""
    token = await verify_token(credentials.credentials)
    roles = set(token.get("roles", []))
    if not roles.intersection({"admin", "platform_admin"}):
        raise HTTPException(403, "admin privileges required")
    return token


@router.get("/catalog")
async def database_catalog(_: dict = Depends(require_admin)):
    return {
        "version": 1,
        "policy": "capability-driven",
        "sql_endpoint": False,
        "databases": catalog(),
    }


@router.get("/reconcile")
async def database_reconcile(_: dict = Depends(require_admin)):
    """Reconcile declared capabilities against the live PostgreSQL server."""
    try:
        return await reconcile_postgres()
    except Exception as exc:
        raise HTTPException(503, "live PostgreSQL discovery unavailable") from exc
