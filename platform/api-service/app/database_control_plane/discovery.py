"""Read-only live datastore discovery for the admin control plane.

Discovery observes PostgreSQL metadata only. It never executes user SQL and
never grants mutation capabilities.
"""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.database_control_plane.registry import DATABASE_CAPABILITIES

_SYSTEM_DATABASES = {"postgres", "template0", "template1"}
_EXCLUDED_SCHEMAS = {"pg_catalog", "information_schema"}
def _postgres_dsn(database: str) -> str:
    url = make_url(settings.database_url).set(database=database)
    return url.render_as_string(hide_password=False).replace("+asyncpg", "")


def _declared_by_database() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in DATABASE_CAPABILITIES:
        result.setdefault(item.database, []).append(item.service)
    return result


async def _connect(database: str) -> asyncpg.Connection:
    return await asyncio.wait_for(asyncpg.connect(dsn=_postgres_dsn(database)), timeout=3.0)


async def _inspect_database(database: str) -> dict[str, Any]:
    conn = await _connect(database)
    try:
        schemas = [r["schema_name"] for r in await conn.fetch(
            """select schema_name from information_schema.schemata
               where schema_name <> all($1::text[]) order by schema_name""",
            list(_EXCLUDED_SCHEMAS),
        )]
        tables = await conn.fetch(
            """select c.table_schema, c.table_name
               from information_schema.tables c
               where c.table_type = 'BASE TABLE'
                 and c.table_schema <> all($1::text[])
               order by c.table_schema, c.table_name""",
            list(_EXCLUDED_SCHEMAS),
        )
        table_items: list[dict[str, Any]] = []
        for row in tables:
            schema, name = row["table_schema"], row["table_name"]
            columns = await conn.fetch(
                """select column_name, data_type, is_nullable, ordinal_position
                   from information_schema.columns
                   where table_schema=$1 and table_name=$2
                   order by ordinal_position""", schema, name)
            constraints = await conn.fetch(
                """select tc.constraint_name, tc.constraint_type,
                          array_agg(kcu.column_name order by kcu.ordinal_position) as columns
                   from information_schema.table_constraints tc
                   left join information_schema.key_column_usage kcu
                     on kcu.constraint_name=tc.constraint_name
                    and kcu.table_schema=tc.table_schema
                    and kcu.table_name=tc.table_name
                   where tc.table_schema=$1 and tc.table_name=$2
                   group by tc.constraint_name, tc.constraint_type
                   order by tc.constraint_name""", schema, name)
            indexes = await conn.fetch(
                """select indexname, indexdef from pg_indexes
                   where schemaname=$1 and tablename=$2 order by indexname""", schema, name)
            table_items.append({
                "schema": schema,
                "name": name,
                "columns": [dict(r) for r in columns],
                "constraints": [dict(r) for r in constraints],
                "indexes": [dict(r) for r in indexes],
            })
        return {"database": database, "reachable": True, "schemas": schemas, "tables": table_items}
    finally:
        await conn.close()
async def discover_postgres() -> dict[str, Any]:
    """Return live PostgreSQL inventory reconciled with declared capabilities."""
    conn = await _connect(make_url(settings.database_url).database or "postgres")
    try:
        rows = await conn.fetch(
            """select datname, pg_size_pretty(pg_database_size(datname)) as size,
                      pg_database_size(datname) as size_bytes
               from pg_database
               where datallowconn and not datistemplate
               order by datname"""
        )
    finally:
        await conn.close()

    declared = _declared_by_database()
    semaphore = asyncio.Semaphore(3)

    async def inspect(row: Any) -> dict[str, Any]:
        name = row["datname"]
        item: dict[str, Any] = {
            "database": name,
            "size": row["size"],
            "size_bytes": row["size_bytes"],
            "declared_services": declared.get(name, []),
            "declaration_status": "declared" if name in declared else "live_undeclared",
        }
        if name in _SYSTEM_DATABASES:
            item["classification"] = "system"
            item["reachable"] = True
            return item
        async with semaphore:
            try:
                item.update(await asyncio.wait_for(_inspect_database(name), timeout=12.0))
                item["classification"] = "application"
            except Exception as exc:
                item.update({"reachable": False, "error_type": type(exc).__name__})
        return item

    databases = list(await asyncio.gather(*(inspect(row) for row in rows)))

    declared_only = [
        {"database": name, "services": services, "declaration_status": "declared_not_live"}
        for name, services in sorted(declared.items())
        if not any(d["database"] == name for d in databases)
    ]
    return {"databases": databases, "declared_not_live": declared_only}
async def reconcile_postgres() -> dict[str, Any]:
    """Small, bounded reconciliation suitable for an authenticated admin call."""
    result = await discover_postgres()
    live = result["databases"]
    return {
        "version": 1,
        "source": "live-postgresql",
        "read_only": True,
        "sql_endpoint": False,
        "summary": {
            "live_databases": len(live),
            "reachable_databases": sum(1 for d in live if d.get("reachable")),
            "live_undeclared": sum(1 for d in live if d.get("declaration_status") == "live_undeclared"),
            "declared_not_live": len(result["declared_not_live"]),
        },
        **result,
    }
