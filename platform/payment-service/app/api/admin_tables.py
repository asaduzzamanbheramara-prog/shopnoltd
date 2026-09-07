"""High-privilege database control-plane API.

This module intentionally uses SQLAlchemy Core metadata rather than arbitrary
SQL text. It is restricted to platform administrators and provides validated
CRUD, filtering, bulk deletion, import/export, and aggregate inspection.
Every mutation is transactionally audit logged; system/audit tables are
read-only through this generic surface.
"""
import csv
import io
import json
import uuid
from datetime import date, datetime
from decimal import Decimal

from app.api.admin import require_admin
from app.core.db import Base, SessionLocal
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

READ_ONLY_TABLES = {"admin_audit_log", "alembic_version"}
MAX_PAGE_SIZE = 500
MAX_IMPORT_ROWS = 5000


async def db():
    async with SessionLocal() as s:
        yield s


def _serialize(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _row_to_dict(row, table) -> dict:
    return {col.name: _serialize(getattr(row, col.name)) for col in table.columns}


def _get_table(name: str):
    table = Base.metadata.tables.get(name)
    if table is None:
        raise HTTPException(404, f"No table named '{name}'")
    return table


def _pk_column(table):
    pk_cols = list(table.primary_key.columns)
    if len(pk_cols) != 1:
        raise HTTPException(
            400,
            f"Table '{table.name}' has {len(pk_cols)} primary key columns; "
            "use the service-specific API for composite-key records.",
        )
    return pk_cols[0]


def _write_allowed(table_name: str):
    if table_name in READ_ONLY_TABLES:
        raise HTTPException(403, f"Table '{table_name}' is read-only")


def _columns(table):
    return {col.name: col for col in table.columns}


def _validate_payload(table, payload: dict):
    if not isinstance(payload, dict):
        raise HTTPException(400, "payload must be an object")
    cols = _columns(table)
    unknown = set(payload) - set(cols)
    if unknown:
        raise HTTPException(400, f"Unknown column(s): {', '.join(sorted(unknown))}")
    return cols


def _audit_table():
    table = Base.metadata.tables.get("admin_audit_log")
    if table is None:
        raise HTTPException(503, "admin_audit_log migration is required before database writes")
    return table


async def _write_audit_log(s, actor, action, table_name, record_id, before, after):
    audit = _audit_table()
    await s.execute(
        insert(audit).values(
            id=uuid.uuid4(),
            actor=actor,
            action=action,
            table_name=table_name,
            record_id=str(record_id) if record_id is not None else None,
            before=json.dumps(before, default=str) if before is not None else None,
            after=json.dumps(after, default=str) if after is not None else None,
            created_at=datetime.utcnow(),
        )
    )


def _where_filter(table, search: str | None, column: str | None):
    if not search:
        return None
    cols = _columns(table)
    if column:
        if column not in cols:
            raise HTTPException(400, f"Unknown filter column '{column}'")
        return cols[column].cast(str).ilike(f"%{search}%")
    return func.concat_ws(
        " ", *[col.cast(str) for col in table.columns]
    ).ilike(f"%{search}%")


@router.get("/tables")
async def list_tables(user=Depends(require_admin)):
    return [
        {
            "name": name,
            "read_only": name in READ_ONLY_TABLES,
            "columns": [
                {
                    "name": col.name,
                    "type": str(col.type),
                    "primary_key": bool(col.primary_key),
                    "nullable": bool(col.nullable),
                }
                for col in table.columns
            ],
        }
        for name, table in sorted(Base.metadata.tables.items())
    ]


@router.get("/tables/{table_name}")
async def list_rows(
    table_name: str,
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    search_column: str | None = Query(None, max_length=100),
    sort: str | None = Query(None, max_length=100),
    descending: bool = False,
    user=Depends(require_admin),
    s: AsyncSession = Depends(db),
):
    table = _get_table(table_name)
    columns = _columns(table)
    stmt = select(table)
    predicate = _where_filter(table, search, search_column)
    if predicate is not None:
        stmt = stmt.where(predicate)
    if sort:
        if sort not in columns:
            raise HTTPException(400, f"Unknown sort column '{sort}'")
        stmt = stmt.order_by(columns[sort].desc() if descending else columns[sort].asc())
    else:
        pk = list(table.primary_key.columns)
        if pk:
            stmt = stmt.order_by(pk[0].asc())
    count_stmt = select(func.count()).select_from(table)
    if predicate is not None:
        count_stmt = count_stmt.where(predicate)
    total = int((await s.execute(count_stmt)).scalar_one())
    result = await s.execute(stmt.limit(limit).offset(offset))
    return {
        "table": table_name,
        "limit": limit,
        "offset": offset,
        "total": total,
        "has_more": offset + limit < total,
        "rows": [_row_to_dict(row, table) for row in result.fetchall()],
    }


@router.get("/tables/{table_name}/analysis")
async def analyze_table(table_name: str, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    table = _get_table(table_name)
    total = int((await s.execute(select(func.count()).select_from(table))).scalar_one())
    return {
        "table": table_name,
        "rows": total,
        "columns": len(table.columns),
        "primary_key": [c.name for c in table.primary_key.columns],
        "nullable_columns": [c.name for c in table.columns if c.nullable],
        "read_only": table_name in READ_ONLY_TABLES,
    }


@router.post("/tables/{table_name}")
async def create_row(table_name: str, payload: dict, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    table = _get_table(table_name)
    _write_allowed(table_name)
    _validate_payload(table, payload)
    try:
        result = await s.execute(insert(table).values(**payload).returning(*table.columns))
        row = result.fetchone()
        if row is None:
            raise HTTPException(400, "insert returned no record")
        values = _row_to_dict(row, table)
        pk = _pk_column(table)
        await _write_audit_log(s, user["sub"], "create", table_name, values.get(pk.name), None, values)
        await s.commit()
        return values
    except HTTPException:
        await s.rollback()
        raise
    except Exception as exc:
        await s.rollback()
        raise HTTPException(409, f"create failed: {exc}") from exc


@router.put("/tables/{table_name}/{record_id}")
async def update_row(table_name: str, record_id: str, payload: dict, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    table = _get_table(table_name)
    _write_allowed(table_name)
    pk = _pk_column(table)
    _validate_payload(table, payload)
    try:
        before_result = await s.execute(select(table).where(pk == record_id))
        before_row = before_result.fetchone()
        if before_row is None:
            raise HTTPException(404, "Record not found")
        before = _row_to_dict(before_row, table)
        await s.execute(update(table).where(pk == record_id).values(**payload))
        after_result = await s.execute(select(table).where(pk == record_id))
        after_row = after_result.fetchone()
        after = _row_to_dict(after_row, table)
        await _write_audit_log(s, user["sub"], "update", table_name, record_id, before, after)
        await s.commit()
        return after
    except HTTPException:
        await s.rollback()
        raise
    except Exception as exc:
        await s.rollback()
        raise HTTPException(409, f"update failed: {exc}") from exc


@router.delete("/tables/{table_name}/{record_id}")
async def delete_row(table_name: str, record_id: str, confirm: bool = False, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    table = _get_table(table_name)
    _write_allowed(table_name)
    if not confirm:
        raise HTTPException(400, "destructive delete requires confirm=true")
    pk = _pk_column(table)
    try:
        before_result = await s.execute(select(table).where(pk == record_id))
        before_row = before_result.fetchone()
        if before_row is None:
            raise HTTPException(404, "Record not found")
        before = _row_to_dict(before_row, table)
        await s.execute(delete(table).where(pk == record_id))
        await _write_audit_log(s, user["sub"], "delete", table_name, record_id, before, None)
        await s.commit()
        return {"ok": True, "deleted": 1}
    except HTTPException:
        await s.rollback()
        raise
    except Exception as exc:
        await s.rollback()
        raise HTTPException(409, f"delete failed: {exc}") from exc


@router.post("/tables/{table_name}/bulk-delete")
async def bulk_delete(table_name: str, ids: list[str], confirm: bool = False, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    table = _get_table(table_name)
    _write_allowed(table_name)
    if not confirm:
        raise HTTPException(400, "bulk deletion requires confirm=true")
    if not ids or len(ids) > 500:
        raise HTTPException(400, "ids must contain 1..500 records")
    pk = _pk_column(table)
    try:
        result = await s.execute(select(table).where(pk.in_(ids)))
        rows = result.fetchall()
        for row in rows:
            before = _row_to_dict(row, table)
            await _write_audit_log(s, user["sub"], "delete", table_name, before.get(pk.name), before, None)
        await s.execute(delete(table).where(pk.in_(ids)))
        await s.commit()
        return {"ok": True, "requested": len(ids), "deleted": len(rows)}
    except HTTPException:
        await s.rollback()
        raise
    except Exception as exc:
        await s.rollback()
        raise HTTPException(409, f"bulk delete failed: {exc}") from exc


@router.get("/tables/{table_name}/export")
async def export_table(
    table_name: str,
    format: str = Query("json", pattern="^(json|csv)$"),
    search: str | None = Query(None, max_length=200),
    search_column: str | None = Query(None, max_length=100),
    user=Depends(require_admin),
    s: AsyncSession = Depends(db),
):
    table = _get_table(table_name)
    predicate = _where_filter(table, search, search_column)
    stmt = select(table)
    if predicate is not None:
        stmt = stmt.where(predicate)
    result = await s.execute(stmt)
    rows = [_row_to_dict(row, table) for row in result.fetchall()]
    if format == "json":
        payload = json.dumps({"table": table_name, "rows": rows}, indent=2, default=str).encode()
        return StreamingResponse(io.BytesIO(payload), media_type="application/json", headers={"Content-Disposition": f"attachment; filename={table_name}.json"})
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[c.name for c in table.columns])
    writer.writeheader()
    writer.writerows(rows)
    return StreamingResponse(io.StringIO(output.getvalue()), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={table_name}.csv"})


@router.post("/tables/{table_name}/import")
async def import_table(table_name: str, file: UploadFile = File(...), user=Depends(require_admin), s: AsyncSession = Depends(db)):
    table = _get_table(table_name)
    _write_allowed(table_name)
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "CSV import is required")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "CSV exceeds 10 MiB limit")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        rows = list(reader)
    except Exception as exc:
        raise HTTPException(400, f"invalid CSV: {exc}") from exc
    if not rows or len(rows) > MAX_IMPORT_ROWS:
        raise HTTPException(400, f"CSV must contain 1..{MAX_IMPORT_ROWS} data rows")
    valid = set(_columns(table))
    unknown = set(reader.fieldnames or []) - valid
    if unknown:
        raise HTTPException(400, f"Unknown CSV column(s): {', '.join(sorted(unknown))}")
    try:
        inserted = 0
        pk = _pk_column(table)
        for payload in rows:
            payload = {k: v for k, v in payload.items() if v != ""}
            _validate_payload(table, payload)
            result = await s.execute(insert(table).values(**payload).returning(*table.columns))
            row = result.fetchone()
            values = _row_to_dict(row, table)
            await _write_audit_log(s, user["sub"], "import", table_name, values.get(pk.name), None, values)
            inserted += 1
        await s.commit()
        return {"ok": True, "inserted": inserted, "filename": file.filename}
    except HTTPException:
        await s.rollback()
        raise
    except Exception as exc:
        await s.rollback()
        raise HTTPException(409, f"import rolled back: {exc}") from exc
