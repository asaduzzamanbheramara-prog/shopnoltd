import pytest
from fastapi import HTTPException

from app.core import security


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claims,tenant_id,allowed",
    [
        ({"sub": "admin-1", "roles": ["platform_admin"]}, "tenant-b", True),
        ({"sub": "admin-2", "roles": ["admin"]}, "tenant-b", True),
        ({"sub": "owner-1", "roles": ["tenant_owner"], "tenant_id": "tenant-a"}, "tenant-a", True),
        ({"sub": "owner-1", "roles": ["tenant_owner"], "tenant_id": "tenant-a"}, "tenant-b", False),
        ({"sub": "customer-1", "roles": ["customer"], "tenant_id": "tenant-a"}, "tenant-a", False),
        ({"sub": "customer-1", "roles": ["customer"], "tenant_id": "tenant-a"}, "tenant-b", False),
    ],
)
async def test_tenant_owner_access_enforces_management_boundary(monkeypatch, claims, tenant_id, allowed):
    async def fake_verify_token(_token):
        return claims

    monkeypatch.setattr(security, "verify_token", fake_verify_token)
    if allowed:
        assert await security.require_tenant_owner_access("token", tenant_id) == claims
    else:
        with pytest.raises(HTTPException) as exc:
            await security.require_tenant_owner_access("token", tenant_id)
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_customer_role_still_has_scoped_tenant_access(monkeypatch):
    claims = {"sub": "customer-1", "roles": ["customer"], "tenant_id": "tenant-a"}

    async def fake_verify_token(_token):
        return claims

    monkeypatch.setattr(security, "verify_token", fake_verify_token)
    assert await security.require_tenant_access("token", "tenant-a") == claims
    with pytest.raises(PermissionError):
        await security.require_tenant_access("token", "tenant-b")
