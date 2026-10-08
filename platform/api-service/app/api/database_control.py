"""Capability-gated generic database inspection for administrators.

Unknown live tables are read-only by default. No arbitrary SQL is accepted.
"""
from __future__ import annotations

import csv
import io
import json
import re

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Any
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import verify_token
from app.database_control_plane.access import resolve_table_capability
from app.database_control_plane.discovery import _connect, discover_postgres

router = APIRouter(prefix="/admin/database", tags=["admin-database"])
bearer = HTTPBearer(auto_error=True)
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    token = await verify_token(credentials.credentials)
    if not set(token.get("roles", [])).intersection({"admin", "platform_admin"}):
        raise HTTPException(403, "admin privileges required")
    return token


def _ident(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise HTTPException(400, "invalid database identifier")
    return '"' + value.replace('"', '""') + '"'


async def _connect_database(database: str):
    try:
        return await _connect(database)
    except Exception as exc:
        raise HTTPException(503, "database unavailable") from exc


@router.get("/tables/{database}/{schema}/{table}/rows")
async def table_rows(
    database: str,
    schema: str,
    table: str,
    _: dict = Depends(require_admin),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str = Query("", max_length=200),
):
    capability = resolve_table_capability(database, table, schema)
    if not capability["readable"]:
        raise HTTPException(403, "table is not readable")
    conn = await _connect_database(database)
    try:
        s, t = _ident(schema), _ident(table)
        columns = await conn.fetch(
            """select c.column_name, c.data_type, c.is_nullable,
                      exists (
                        select 1 from information_schema.table_constraints tc
                        join information_schema.key_column_usage kcu
                          on kcu.constraint_name=tc.constraint_name
                         and kcu.constraint_schema=tc.constraint_schema
                         and kcu.table_schema=tc.table_schema
                         and kcu.table_name=tc.table_name
                        where tc.table_schema=c.table_schema and tc.table_name=c.table_name
                          and tc.constraint_type='PRIMARY KEY' and kcu.column_name=c.column_name
                      ) as primary_key
               from information_schema.columns c
               where c.table_schema=$1 and c.table_name=$2 order by c.ordinal_position""", schema, table
        )
        search = q.strip()
        params: list[Any] = [offset, limit]
        where = ""
        if search:
            clauses = [f"coalesce({_ident(row['column_name'])}::text, '') ILIKE $3" for row in columns]
            where = " WHERE " + " OR ".join(clauses)
            params.append(f"%{search}%")
        rows = await conn.fetch(f"SELECT * FROM {s}.{t}{where} ORDER BY ctid OFFSET $1 LIMIT $2", *params)
        return {
            "database": database, "schema": schema, "table": table,
            "capability": capability,
            "columns": [dict(c) for c in columns],
            "rows": [dict(r) for r in rows], "limit": limit, "offset": offset, "search": search,
        }
    finally:
        await conn.close()



@router.get("/tables/{database}/{schema}/{table}/count")
async def table_count(database: str, schema: str, table: str, _: dict = Depends(require_admin)):
    capability = resolve_table_capability(database, table, schema)
    if not capability["readable"]:
        raise HTTPException(403, "table is not readable")
    conn = await _connect_database(database)
    try:
        exists = await conn.fetchval(
            "select 1 from information_schema.tables where table_schema=$1 and table_name=$2",
            schema, table
        )
        if not exists:
            raise HTTPException(404, "table not found")
        count = await conn.fetchval("SELECT count(*) FROM " + _ident(schema) + "." + _ident(table))
        return {"database": database, "schema": schema, "table": table, "total": count, "capability": capability}
    finally:
        await conn.close()


@router.get("/tables/{database}/{schema}/{table}/analysis")
async def table_analysis(database: str, schema: str, table: str, _: dict = Depends(require_admin)):
    capability = resolve_table_capability(database, table, schema)
    if not capability["readable"]:
        raise HTTPException(403, "table is not readable")
    conn = await _connect_database(database)
    try:
        exists = await conn.fetchval(
            "select 1 from information_schema.tables where table_schema=$1 and table_name=$2",
            schema, table,
        )
        if not exists:
            raise HTTPException(404, "table not found")
        columns = await conn.fetch(
            """select column_name, data_type, is_nullable, ordinal_position
               from information_schema.columns where table_schema=$1 and table_name=$2
               order by ordinal_position""", schema, table
        )
        constraints = await conn.fetch(
            """select tc.constraint_name, tc.constraint_type,
                      array_agg(kcu.column_name order by kcu.ordinal_position) as columns
               from information_schema.table_constraints tc
               left join information_schema.key_column_usage kcu
                 on kcu.constraint_name=tc.constraint_name
                and kcu.constraint_schema=tc.constraint_schema
                and kcu.table_schema=tc.table_schema
                and kcu.table_name=tc.table_name
               where tc.table_schema=$1 and tc.table_name=$2
               group by tc.constraint_name, tc.constraint_type
               order by tc.constraint_name""", schema, table
        )
        indexes = await conn.fetch(
            "select indexname, indexdef from pg_indexes where schemaname=$1 and tablename=$2 order by indexname",
            schema, table,
        )
        rows = await conn.fetchval("SELECT count(*) FROM " + _ident(schema) + "." + _ident(table))
        primary_key = []
        for item in constraints:
            if item["constraint_type"] == "PRIMARY KEY":
                primary_key = list(item["columns"] or [])
                break
        return {
            "database": database, "schema": schema, "table": table,
            "rows": rows, "columns": len(columns), "primary_key": primary_key,
            "unique_constraints": [dict(r) for r in constraints if r["constraint_type"] == "UNIQUE"],
            "constraints": [dict(r) for r in constraints],
            "indexes": [dict(r) for r in indexes],
            "capability": capability,
        }
    finally:
        await conn.close()


@router.post("/tables/{database}/{schema}/{table}/rows", status_code=201)
async def insert_row(database: str, schema: str, table: str, values: dict[str, Any] = Body(...), _: dict = Depends(require_admin)):
    capability = resolve_table_capability(database, table, schema)
    if not capability["writable"]:
        raise HTTPException(403, capability.get("protected_reason") or "insert disabled")
    if not values:
        raise HTTPException(400, "values cannot be empty")
    conn = await _connect_database(database)
    try:
        columns = await conn.fetch(
            "select column_name, is_generated from information_schema.columns where table_schema=$1 and table_name=$2",
            schema, table
        )
        allowed = {r["column_name"] for r in columns if r["is_generated"] == "NEVER"}
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise HTTPException(400, {"detail": "unknown columns", "columns": unknown})
        names = list(values)
        sql = "INSERT INTO " + _ident(schema) + "." + _ident(table) + " (" + ", ".join(_ident(n) for n in names) + ") VALUES (" + ", ".join("$" + str(i + 1) for i in range(len(names))) + ") RETURNING *"
        row = await conn.fetchrow(sql, *[values[n] for n in names])
        return {"row": dict(row), "capability": capability}
    finally:
        await conn.close()


@router.patch("/tables/{database}/{schema}/{table}/rows")
async def update_row(database: str, schema: str, table: str, payload: dict[str, Any] = Body(...), _: dict = Depends(require_admin)):
    capability = resolve_table_capability(database, table, schema)
    if not capability["writable"]:
        raise HTTPException(403, capability.get("protected_reason") or "update disabled")
    key, values = payload.get("key"), payload.get("values")
    if not isinstance(key, dict) or not key or not isinstance(values, dict) or not values:
        raise HTTPException(400, "body must contain non-empty key and values objects")
    conn = await _connect_database(database)
    try:
        columns = await conn.fetch("select column_name from information_schema.columns where table_schema=$1 and table_name=$2", schema, table)
        allowed = {r["column_name"] for r in columns}
        if set(key) - allowed or set(values) - allowed:
            raise HTTPException(400, "unknown column supplied")
        pk = await conn.fetch(
            "select kcu.column_name from information_schema.table_constraints tc join information_schema.key_column_usage kcu on kcu.constraint_name=tc.constraint_name and kcu.constraint_schema=tc.constraint_schema and kcu.table_schema=tc.table_schema and kcu.table_name=tc.table_name where tc.table_schema=$1 and tc.table_name=$2 and tc.constraint_type='PRIMARY KEY' order by kcu.ordinal_position",
            schema, table
        )
        primary_key = [r["column_name"] for r in pk]
        if not primary_key or set(key) != set(primary_key):
            raise HTTPException(409, {"detail": "complete primary key is required", "primary_key": primary_key})
        names, key_names = list(values), list(key)
        assignments = [_ident(n) + " = $" + str(i + 1) for i, n in enumerate(names)]
        where = " AND ".join(_ident(n) + " = $" + str(len(names) + i + 1) for i, n in enumerate(key_names))
        sql = "UPDATE " + _ident(schema) + "." + _ident(table) + " SET " + ", ".join(assignments) + " WHERE " + where + " RETURNING *"
        row = await conn.fetchrow(sql, *[values[n] for n in names], *[key[n] for n in key_names])
        if row is None:
            raise HTTPException(404, "row not found")
        return {"row": dict(row), "capability": capability}
    finally:
        await conn.close()


@router.delete("/tables/{database}/{schema}/{table}/rows")
async def delete_row(database: str, schema: str, table: str, payload: dict[str, Any] = Body(...), _: dict = Depends(require_admin)):
    capability = resolve_table_capability(database, table, schema)
    if not capability["destructive"]:
        raise HTTPException(403, capability.get("protected_reason") or "delete disabled")
    key = payload.get("key")
    if not isinstance(key, dict) or not key:
        raise HTTPException(400, "body must contain a key object")
    conn = await _connect_database(database)
    try:
        pk = await conn.fetch(
            "select kcu.column_name from information_schema.table_constraints tc join information_schema.key_column_usage kcu on kcu.constraint_name=tc.constraint_name and kcu.constraint_schema=tc.constraint_schema and kcu.table_schema=tc.table_schema and kcu.table_name=tc.table_name where tc.table_schema=$1 and tc.table_name=$2 and tc.constraint_type='PRIMARY KEY' order by kcu.ordinal_position",
            schema, table
        )
        primary_key = [r["column_name"] for r in pk]
        if not primary_key or set(key) != set(primary_key):
            raise HTTPException(409, {"detail": "complete primary key is required", "primary_key": primary_key})
        where = " AND ".join(_ident(n) + " = $" + str(i + 1) for i, n in enumerate(primary_key))
        row = await conn.fetchrow("DELETE FROM " + _ident(schema) + "." + _ident(table) + " WHERE " + where + " RETURNING *", *[key[n] for n in primary_key])
        if row is None:
            raise HTTPException(404, "row not found")
        return {"deleted": dict(row), "capability": capability}
    finally:
        await conn.close()


@router.get("/tables/{database}/{schema}/{table}/export")
async def export_table(
    database: str, schema: str, table: str,
    _: dict = Depends(require_admin),
    limit: int = Query(5000, ge=1, le=10000),
):
    capability = resolve_table_capability(database, table, schema)
    if not capability["exportable"]:
        raise HTTPException(403, "table export is disabled")
    conn = await _connect_database(database)
    try:
        rows = await conn.fetch(f"SELECT * FROM {_ident(schema)}.{_ident(table)} LIMIT $1", limit)
        payload = json.dumps([dict(row) for row in rows], default=str, ensure_ascii=False)
        return Response(payload, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{database}-{table}.json"'})
    finally:
        await conn.close()



@router.post("/tables/{database}/{schema}/{table}/import")
async def import_rows(
    database: str,
    schema: str,
    table: str,
    payload: dict[str, Any] = Body(...),
    _: dict = Depends(require_admin),
):
    """Transactional JSON import for explicitly importable writable tables."""
    capability = resolve_table_capability(database, table, schema)
    if not capability["importable"] or not capability["writable"]:
        raise HTTPException(403, capability.get("protected_reason") or "import disabled")
    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows or len(rows) > 5000 or not all(isinstance(row, dict) and row for row in rows):
        raise HTTPException(400, "rows must be a non-empty array of objects with at most 5000 rows")
    conn = await _connect_database(database)
    try:
        columns = await conn.fetch(
            "select column_name, is_generated from information_schema.columns where table_schema=$1 and table_name=$2",
            schema, table,
        )
        allowed = {row["column_name"] for row in columns if row["is_generated"] == "NEVER"}
        if any(set(row) - allowed for row in rows):
            raise HTTPException(400, "import contains unknown or generated columns")
        async with conn.transaction():
            inserted = []
            for row in rows:
                names = list(row)
                sql = (
                    "INSERT INTO " + _ident(schema) + "." + _ident(table)
                    + " (" + ", ".join(_ident(name) for name in names) + ") VALUES ("
                    + ", ".join("$" + str(index + 1) for index in range(len(names))) + ") RETURNING *"
                )
                inserted.append(dict(await conn.fetchrow(sql, *[row[name] for name in names])))
        return {"inserted": len(inserted), "rows": inserted[:20], "truncated": max(0, len(inserted) - 20), "capability": capability}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "import failed; transaction rolled back") from exc
    finally:
        await conn.close()


@router.get("/live-catalog")
async def live_catalog(_: dict = Depends(require_admin)):
    """Live catalog with effective per-table capabilities."""
    result = await discover_postgres()
    for database in result["databases"]:
        for table in database.get("tables", []):
            table["capability"] = resolve_table_capability(database["database"], table["name"], table.get("schema"))
    return result


@router.post("/sql")
async def execute_admin_sql(payload: dict[str, Any] = Body(...), token: dict = Depends(require_admin)):
    """Execute one guarded PostgreSQL statement for platform administrators.

    SELECT/EXPLAIN are allowed for admin inspection. INSERT/UPDATE/DELETE are
    allowed only against explicitly generic-writable tables in the capability
    registry. Multiple statements, transaction-control commands, COPY, and
    database-level commands are rejected.
    """
    sql = str(payload.get("sql") or "").strip()
    database = str(payload.get("database") or "").strip()
    if not sql or not database:
        raise HTTPException(400, "database and sql are required")
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()
    if ";" in sql:
        raise HTTPException(400, "multiple SQL statements are not allowed")
    if "--" in sql or "/*" in sql or "*/" in sql:
        raise HTTPException(400, "SQL comments are not allowed")
    upper = sql.upper()
    first = upper.split(None, 1)[0] if upper.split() else ""
    if first in {"BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE", "COPY", "VACUUM", "REINDEX", "GRANT", "REVOKE", "ALTER", "CREATE", "DROP", "TRUNCATE"}:
        raise HTTPException(403, "statement type is not available through the browser SQL control plane")
    if first not in {"SELECT", "EXPLAIN", "WITH", "INSERT", "UPDATE", "DELETE"}:
        raise HTTPException(400, "only SELECT, EXPLAIN, WITH, INSERT, UPDATE and DELETE are supported")

    if first == "WITH":
        raise HTTPException(403, "WITH statements are read-only through the browser SQL control plane")
    mutation = first in {"INSERT", "UPDATE", "DELETE"}
    if mutation and "platform_admin" not in set(token.get("roles", [])):
        raise HTTPException(403, "platform_admin is required for SQL mutations")
    candidates = re.findall(
        r"\b(?:FROM|JOIN|UPDATE|INTO|DELETE\s+FROM)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\.([A-Za-z_][A-Za-z0-9_]*))?",
        sql,
        flags=re.IGNORECASE,
    )
    tables = {(("public", first_name) if second_name is None else (first_name, second_name)) for first_name, second_name in candidates}
    if any(schema in {"pg_catalog", "information_schema"} for schema, _ in tables):
        raise HTTPException(403, "system catalogs are not available through the browser SQL control plane")
    for schema, table in tables:
        capability = resolve_table_capability(database, table, schema)
        if capability.get("protected_reason"):
            raise HTTPException(403, capability["protected_reason"])
        if not capability["readable"]:
            raise HTTPException(403, f"table {schema}.{table} is not readable")
        if mutation and not capability["writable"]:
            raise HTTPException(403, f"generic SQL mutation is disabled for {schema}.{table}")
    if mutation and not tables:
        raise HTTPException(400, "mutation must name an explicit table")
    if database == "kpi":
        raise HTTPException(400, "MongoDB databases are not supported by the PostgreSQL SQL browser")
    conn = await _connect_database(database)
    try:
        if first in {"SELECT", "EXPLAIN", "WITH"}:
            # Run browser inspection in a read-only transaction so even a
            # callable function cannot perform a write as a side effect.
            async with conn.transaction():
                await conn.execute("SET TRANSACTION READ ONLY")
                rows = await conn.fetch(sql)
            return {
                "database": database,
                "statement_type": first,
                "columns": list(rows[0].keys()) if rows else [],
                "rows": [dict(row) for row in rows[:1000]],
                "row_count": len(rows),
                "truncated": len(rows) > 1000,
            }
        status = await conn.execute(sql)
        return {"database": database, "statement_type": first, "status": status}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"SQL execution failed: {type(exc).__name__}") from exc
    finally:
        await conn.close()
