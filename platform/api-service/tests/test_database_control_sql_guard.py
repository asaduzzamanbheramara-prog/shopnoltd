import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/postgres")

import pytest
from fastapi import HTTPException

from app.api.database_control import _guarded_sql_table_references


def test_extracts_unquoted_and_quoted_table_references():
    assert _guarded_sql_table_references("SELECT * FROM public.users") == {("public", "users")}
    assert _guarded_sql_table_references('SELECT * FROM "public"."users"') == {("public", "users")}
    assert _guarded_sql_table_references('UPDATE "public"."safe_rows" SET value = 1') == {("public", "safe_rows")}


def test_extracts_joined_tables():
    assert _guarded_sql_table_references(
        "SELECT u.id FROM public.users u JOIN public.profiles p ON p.user_id = u.id"
    ) == {("public", "users"), ("public", "profiles")}


def test_does_not_treat_table_words_inside_string_literals_as_references():
    assert _guarded_sql_table_references("SELECT 'FROM public.users' AS example") == set()


def test_rejects_only_parenthesized_table_syntax():
    with pytest.raises(HTTPException) as exc:
        _guarded_sql_table_references("SELECT * FROM ONLY (public.users)")
    assert exc.value.status_code == 403


def test_rejects_unqualified_postgres_system_relations():
    with pytest.raises(HTTPException) as exc:
        _guarded_sql_table_references("SELECT * FROM pg_class")
    assert exc.value.status_code == 403


from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.api import database_control


@pytest.mark.asyncio
async def test_admin_role_cannot_use_platform_admin_guard(monkeypatch):
    monkeypatch.setattr(
        database_control,
        "verify_token",
        AsyncMock(return_value={"roles": ["admin"]}),
    )
    with pytest.raises(HTTPException) as exc:
        await database_control.require_platform_admin(
            SimpleNamespace(credentials="placeholder")
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_platform_admin_passes_platform_admin_guard(monkeypatch):
    token = {"sub": "platform-admin-test", "roles": ["platform_admin"]}
    monkeypatch.setattr(
        database_control,
        "verify_token",
        AsyncMock(return_value=token),
    )
    result = await database_control.require_platform_admin(
        SimpleNamespace(credentials="placeholder")
    )
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
