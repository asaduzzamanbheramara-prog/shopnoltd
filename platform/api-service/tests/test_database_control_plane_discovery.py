import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/postgres")

from fastapi import HTTPException

from app.api.database_control import _guarded_sql_table_references
from app.database_control_plane.discovery import _declared_by_database, _postgres_dsn


def test_declared_database_map_preserves_service_ownership():
    data = _declared_by_database()
    assert "shopnoltd" in data
    assert "payment-service" in data["shopnoltd"]
    assert "ai-platform" in data["ai"]


def test_postgres_dsn_replaces_only_database_name():
    dsn = _postgres_dsn("example_database")
    assert "example_database" in dsn
    assert "+asyncpg" not in dsn



def test_sql_guard_resolves_simple_table_references():
    assert _guarded_sql_table_references("SELECT id FROM public.posts WHERE id = 1") == {("public", "posts")}


def test_sql_guard_rejects_quoted_identifiers_that_bypass_scanner():
    try:
        _guarded_sql_table_references('SELECT * FROM "public"."transactions"')
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("quoted identifiers must fail closed")


def test_sql_guard_rejects_comma_separated_from_lists():
    try:
        _guarded_sql_table_references("SELECT * FROM public.posts, public.transactions")
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("comma-separated FROM lists must fail closed")


def test_sql_guard_rejects_unresolved_table_reference():
    try:
        _guarded_sql_table_references("SELECT * FROM")
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("unresolved table references must fail closed")
