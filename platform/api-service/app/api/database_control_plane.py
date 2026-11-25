"""Unified admin database capability and live inventory control plane.

Discovery is read-only. Mutations remain capability-driven and service-owned.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token
from app.database_control_plane.discovery import discover_mongodb, reconcile_postgres
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
        "version": 2,
        "policy": "capability-driven",
        "sql_endpoint": True,
        "sql_mutation_requires_platform_admin": True,
        "databases": catalog(),
    }


@router.get("/reconcile")
async def database_reconcile(_: dict = Depends(require_admin)):
    """Reconcile declared capabilities against live PostgreSQL and MongoDB stores."""
    try:
        return await reconcile_postgres()
    except Exception as exc:
        raise HTTPException(503, "live datastore discovery unavailable") from exc


@router.get("/mongodb-catalog")
async def mongodb_catalog(_: dict = Depends(require_admin)):
    """Return read-only MongoDB database and collection metadata."""
    try:
        return {"read_only": True, **await discover_mongodb()}
    except Exception as exc:
        raise HTTPException(503, "live MongoDB discovery unavailable") from exc


@router.get("/live-catalog")
async def database_live_catalog(_: dict = Depends(require_admin)):
    """Return the live PostgreSQL inventory in the shape used by the admin portal.

    Keep this compatibility endpoint read-only; /reconcile remains the full
    PostgreSQL + MongoDB diagnostic response.
    """
    try:
        result = await reconcile_postgres()
        postgres = result["postgres"]
        databases = postgres["databases"]
        return {
            "version": result.get("version", 2),
            "source": "live-postgresql",
            "read_only": True,
            "summary": {
                "live_databases": len(databases),
                "reachable_databases": sum(1 for item in databases if item.get("reachable")),
                "declared_not_live": len(postgres.get("declared_not_live", [])),
            },
            "databases": databases,
        }
    except Exception as exc:
        raise HTTPException(503, "live PostgreSQL inventory unavailable") from exc
