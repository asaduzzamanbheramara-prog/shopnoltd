"""Tenant context validation for authenticated payment operations."""

from fastapi import HTTPException


def require_tenant_id(user: dict) -> str:
    """Require a non-empty tenant claim; never silently map users to default."""
    tenant_id = user.get("tenant_id")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise HTTPException(status_code=403, detail="tenant context required")
    return tenant_id.strip()
