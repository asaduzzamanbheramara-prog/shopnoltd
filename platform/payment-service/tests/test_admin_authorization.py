from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api import admin
from app.core import security


def test_realm_roles_excludes_client_scoped_privileges():
    claims = {
        "roles": ["customer"],
        "realm_access": {"roles": ["tenant_owner"]},
        "resource_access": {
            "api-service": {"roles": ["platform_admin", "admin"]},
            "other-client": {"roles": ["tenant_owner"]},
        },
    }
    assert security.realm_roles(claims) == {"customer", "tenant_owner"}


@pytest.mark.asyncio
async def test_client_scoped_platform_admin_cannot_access_financial_admin_routes(monkeypatch):
    claims = {
        "sub": "client-admin",
        "roles": ["platform_admin", "admin"],
        "realm_roles": [],
        "resource_access": {"api-service": {"roles": ["platform_admin", "admin"]}},
    }
    monkeypatch.setattr(admin, "verify_token", AsyncMock(return_value=claims))
    with pytest.raises(HTTPException) as exc:
        await admin.require_admin(SimpleNamespace(credentials="token"))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_realm_platform_admin_can_access_financial_admin_routes(monkeypatch):
    claims = {
        "sub": "realm-admin",
        "roles": ["platform_admin"],
        "realm_roles": ["platform_admin"],
    }
    monkeypatch.setattr(admin, "verify_token", AsyncMock(return_value=claims))
    assert await admin.require_admin(SimpleNamespace(credentials="token")) is claims
