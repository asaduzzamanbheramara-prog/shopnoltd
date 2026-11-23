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
        # An aggregated client role must not become a realm/platform role.
        ({"sub": "client-admin", "roles": ["platform_admin"], "realm_roles": [], "tenant_id": "tenant-a"}, "tenant-b", False),
        ({"sub": "client-owner", "roles": ["tenant_owner"], "realm_roles": [], "tenant_id": "tenant-a"}, "tenant-a", False),
        # A verified realm role remains authoritative even if client roles exist.
        ({"sub": "realm-admin", "roles": ["platform_admin"], "realm_roles": ["platform_admin"], "tenant_id": "tenant-a"}, "tenant-b", True),
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


def test_realm_roles_never_include_resource_access_roles():
    claims = {
        "roles": ["customer"],
        "realm_access": {"roles": ["tenant_owner"]},
        "resource_access": {
            "api-service": {"roles": ["platform_admin", "admin"]},
            "unrelated-client": {"roles": ["tenant_owner"]},
        },
    }
    assert security.realm_roles(claims) == {"customer", "tenant_owner"}


def test_explicit_empty_realm_roles_blocks_aggregated_client_role_fallback():
    claims = {
        "roles": ["platform_admin"],
        "realm_roles": [],
        "resource_access": {"api-service": {"roles": ["platform_admin"]}},
    }
    assert security.realm_roles(claims) == set()
