import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/postgres")

from fastapi import HTTPException

from app.api.database_control import _guarded_sql_table_references
from app.database_control_plane.contract import DatastoreKind\nfrom app.database_control_plane import discovery\nfrom app.database_control_plane.discovery import _declared_by_database, _postgres_dsn


def test_declared_database_map_preserves_service_ownership():
    data = _declared_by_database(DatastoreKind.POSTGRESQL)
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



def test_inspect_database_batches_catalog_queries(monkeypatch):
    import asyncio

    class FakeConnection:
        def __init__(self):
            self.queries = []

        async def fetch(self, query, *args):
            self.queries.append(query)
            if "information_schema.schemata" in query:
                return [{"schema_name": "public"}]
            if "information_schema.tables" in query:
                return [{"table_schema": "public", "table_name": "orders"}]
            if "information_schema.columns" in query:
                return [{
                    "table_schema": "public", "table_name": "orders",
                    "column_name": "id", "data_type": "bigint",
                    "is_nullable": "NO", "ordinal_position": 1,
                }]
            if "information_schema.table_constraints" in query:
                return [{
                    "table_schema": "public", "table_name": "orders",
                    "constraint_name": "orders_pkey", "constraint_type": "PRIMARY KEY",
                    "columns": ["id"],
                }]
            if "from pg_indexes" in query:
                return [{
                    "table_schema": "public", "table_name": "orders",
                    "indexname": "orders_pkey", "indexdef": "CREATE UNIQUE INDEX orders_pkey",
                }]
            raise AssertionError("unexpected catalog query")

        async def close(self):
            return None

    connection = FakeConnection()

    async def fake_connect(database):
        assert database == "testdb"
        return connection

    monkeypatch.setattr(discovery, "_connect", fake_connect)
    result = asyncio.run(discovery._inspect_database("testdb"))

    assert len(connection.queries) == 5
    assert result["schemas"] == ["public"]
    assert result["tables"] == [{
        "schema": "public",
        "name": "orders",
        "columns": [{
            "column_name": "id", "data_type": "bigint",
            "is_nullable": "NO", "ordinal_position": 1,
        }],
        "constraints": [{
            "constraint_name": "orders_pkey",
            "constraint_type": "PRIMARY KEY",
            "columns": ["id"],
        }],
        "indexes": [{
            "indexname": "orders_pkey",
            "indexdef": "CREATE UNIQUE INDEX orders_pkey",
        }],
    }]
