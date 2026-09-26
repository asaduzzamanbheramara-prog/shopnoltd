"""Capability-gated generic database inspection for administrators.

Unknown live tables are read-only by default. No arbitrary SQL is accepted.
"""
from __future__ import annotations

import json
import re

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query
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
):
    capability = resolve_table_capability(database, table)
    if not capability["readable"]:
        raise HTTPException(403, "table is not readable")
    conn = await _connect_database(database)
    try:
        s, t = _ident(schema), _ident(table)
        rows = await conn.fetch(f"SELECT * FROM {s}.{t} OFFSET $1 LIMIT $2", offset, limit)
        columns = await conn.fetch(
            """select column_name, data_type, is_nullable from information_schema.columns
               where table_schema=$1 and table_name=$2 order by ordinal_position""", schema, table
        )
        return {
            "database": database, "schema": schema, "table": table,
            "capability": capability,
            "columns": [dict(c) for c in columns],
            "rows": [dict(r) for r in rows], "limit": limit, "offset": offset,
        }
    finally:
        await conn.close()


@router.get("/tables/{database}/{schema}/{table}/export")
async def export_table(
    database: str, schema: str, table: str,
    _: dict = Depends(require_admin),
    limit: int = Query(5000, ge=1, le=10000),
):
    capability = resolve_table_capability(database, table)
    if not capability["exportable"]:
        raise HTTPException(403, "table export is disabled")
    conn = await _connect_database(database)
    try:
        rows = await conn.fetch(f"SELECT * FROM {_ident(schema)}.{_ident(table)} LIMIT $1", limit)
        payload = json.dumps([dict(row) for row in rows], default=str, ensure_ascii=False)
        return Response(payload, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{database}-{table}.json"'})
    finally:
        await conn.close()


@router.get("/live-catalog")
async def live_catalog(_: dict = Depends(require_admin)):
    """Live catalog with effective per-table capabilities."""
    result = await discover_postgres()
    for database in result["databases"]:
        for table in database.get("tables", []):
            table["capability"] = resolve_table_capability(database["database"], table["name"])
    return result
