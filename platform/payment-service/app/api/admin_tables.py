"""Generic admin table browser: list/read/write/delete any table via
SQLAlchemy Core introspection, with every write audit-logged.

Security note: this exposes raw database write access to every mapped
table, gated on the same require_admin dependency as app/api/admin.py.
Treat this as high-privilege surface — it's meant for platform_admin
operators, not regular admin-panel users of a tenant.
"""
import json
import uuid
from datetime import datetime
from decimal import Decimal

from app.api.admin import require_admin
from app.core.db import Base, SessionLocal
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import Table, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


async def db():
    async with SessionLocal() as s:
        yield s


def _serialize(value):
    """Make DB values JSON-safe for the API response and audit log."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _row_to_dict(row, table: Table) -> dict:
    return {col.name: _serialize(getattr(row, col.name)) for col in table.columns}


def _get_table(name: str) -> Table:
    table = Base.metadata.tables.get(name)
    if table is None:
        raise HTTPException(404, f"No table named '{name}'")
    return table


def _pk_column(table: Table):
    pk_cols = list(table.primary_key.columns)
    if len(pk_cols) != 1:
        raise HTTPException(
            400,
            f"Table '{table.name}' has {len(pk_cols)} primary key columns; "
            "this generic browser only supports single-column primary keys.",
        )
    return pk_cols[0]


async def _write_audit_log(
    s: AsyncSession,
    actor: str,
    action: str,
    table_name: str,
    record_id,
    before: dict | None,
    after: dict | None,
):
    audit_table = Base.metadata.tables.get("admin_audit_log")
    if audit_table is None:
        return  # migration not yet applied; don't block the write on it
    await s.execute(
        insert(audit_table).values(
            id=uuid.uuid4(),
            actor=actor,
            action=action,
            table_name=table_name,
            record_id=str(record_id) if record_id is not None else None,
            before=json.dumps(before) if before is not None else None,
            after=json.dumps(after) if after is not None else None,
            created_at=datetime.utcnow(),
        )
    )


@router.get("/tables")
async def list_tables(user=Depends(require_admin)):
    """List every mapped table and its columns."""
    return [
        {
            "name": name,
            "columns": [
                {
                    "name": col.name,
                    "type": str(col.type),
                    "primary_key": col.primary_key,
                    "nullable": col.nullable,
                }
                for col in table.columns
            ],
        }
        for name, table in sorted(Base.metadata.tables.items())
    ]


@router.get("/tables/{table_name}")
async def list_rows(
    table_name: str,
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    user=Depends(require_admin),
    s: AsyncSession = Depends(db),
):
    table = _get_table(table_name)
    result = await s.execute(select(table).limit(limit).offset(offset))
    rows = result.fetchall()
    return {
        "table": table_name,
        "limit": limit,
        "offset": offset,
        "rows": [_row_to_dict(row, table) for row in rows],
    }


@router.post("/tables/{table_name}")
async def create_row(
    table_name: str,
    payload: dict,
    user=Depends(require_admin),
    s: AsyncSession = Depends(db),
):
    table = _get_table(table_name)
    valid_cols = {col.name for col in table.columns}
    unknown = set(payload) - valid_cols
    if unknown:
        raise HTTPException(400, f"Unknown column(s): {', '.join(unknown)}")

    result = await s.execute(insert(table).values(**payload).returning(*table.columns))
    row = result.fetchone()
    new_values = _row_to_dict(row, table)
    pk_col = _pk_column(table)
    await _write_audit_log(
        s, user["sub"], "create", table_name, new_values.get(pk_col.name), None, new_values
    )
    await s.commit()
    return new_values


@router.put("/tables/{table_name}/{record_id}")
async def update_row(
    table_name: str,
    record_id: str,
    payload: dict,
    user=Depends(require_admin),
    s: AsyncSession = Depends(db),
):
    table = _get_table(table_name)
    pk_col = _pk_column(table)
    valid_cols = {col.name for col in table.columns}
    unknown = set(payload) - valid_cols
    if unknown:
        raise HTTPException(400, f"Unknown column(s): {', '.join(unknown)}")

    before_result = await s.execute(select(table).where(pk_col == record_id))
    before_row = before_result.fetchone()
    if before_row is None:
        raise HTTPException(404, "Record not found")
    before_values = _row_to_dict(before_row, table)

    await s.execute(update(table).where(pk_col == record_id).values(**payload))
    after_result = await s.execute(select(table).where(pk_col == record_id))
    after_values = _row_to_dict(after_result.fetchone(), table)

    await _write_audit_log(
        s, user["sub"], "update", table_name, record_id, before_values, after_values
    )
    await s.commit()
    return after_values


@router.delete("/tables/{table_name}/{record_id}")
async def delete_row(
    table_name: str,
    record_id: str,
    user=Depends(require_admin),
    s: AsyncSession = Depends(db),
):
    table = _get_table(table_name)
    pk_col = _pk_column(table)

    before_result = await s.execute(select(table).where(pk_col == record_id))
    before_row = before_result.fetchone()
    if before_row is None:
        raise HTTPException(404, "Record not found")
    before_values = _row_to_dict(before_row, table)

    await s.execute(delete(table).where(pk_col == record_id))
    await _write_audit_log(
        s, user["sub"], "delete", table_name, record_id, before_values, None
    )
    await s.commit()
    return {"ok": True}
