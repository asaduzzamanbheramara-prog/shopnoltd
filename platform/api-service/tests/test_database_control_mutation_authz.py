"""Authorization regression tests for generic database mutation endpoints."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api import database_control


def test_admin_role_cannot_use_platform_admin_guard(monkeypatch):
    monkeypatch.setattr(
        database_control,
        "verify_token",
        AsyncMock(return_value={"roles": ["admin"]}),
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(database_control.require_platform_admin(
            SimpleNamespace(credentials="placeholder")
        ))
    assert exc.value.status_code == 403


def test_platform_admin_passes_platform_admin_guard(monkeypatch):
    token = {"sub": "platform-admin-test", "roles": ["platform_admin"]}
    monkeypatch.setattr(
        database_control,
        "verify_token",
        AsyncMock(return_value=token),
    )
    result = asyncio.run(database_control.require_platform_admin(
        SimpleNamespace(credentials="placeholder")
    ))
    assert result is token


def test_generic_row_mutations_require_platform_admin():
    mutation_methods = {"POST", "PATCH", "DELETE"}
    mutation_routes = [
        route for route in database_control.router.routes
        if getattr(route, "methods", set()) & mutation_methods
        and ("/rows" in route.path or "/import" in route.path)
    ]
    assert mutation_routes, "expected generic row mutation/import routes"
    for route in mutation_routes:
        dependency_calls = {
            dependency.call for dependency in route.dependant.dependencies
        }
        assert database_control.require_platform_admin in dependency_calls, (
            f"{sorted(route.methods)} {route.path} must require platform_admin"
        )
