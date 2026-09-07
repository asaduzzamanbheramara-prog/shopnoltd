"""High-privilege database control-plane API.

Generic table access is deliberately restricted to platform_admin. Normal
admins must use service-specific APIs. No arbitrary SQL is exposed.
"""
import csv
import io
import json
import uuid
from datetime import date, datetime
from decimal import Decimal

from app.api.admin import require_admin
from app.core.db import Base, SessionLocal
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import String, and_, delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
READ_ONLY_TABLES = {"admin_audit_log", "alembic_version"}
MAX_PAGE_SIZE = 500
MAX_IMPORT_ROWS = 5000
MAX_EXPORT_ROWS = 10000

async def db():
    async with SessionLocal() as s:
        yield s

def _platform_admin(user):
    if "platform_admin" not in set(user.get("roles", [])):
        raise HTTPException(403, "platform_admin required for generic database operations")

def _serialize(value):
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, (datetime, date)): return value.isoformat()
    if isinstance(value, uuid.UUID): return str(value)
    return value

def _row_to_dict(row, table):
    return {c.name: _serialize(getattr(row, c.name)) for c in table.columns}

def _table(name):
    table = Base.metadata.tables.get(name)
    if table is None: raise HTTPException(404, f"No table named '{name}'")
    return table

def _pk(table):
    cols = list(table.primary_key.columns)
    if len(cols) != 1:
        raise HTTPException(400, "Generic control-plane operations require a single-column primary key")
    return cols[0]

def _validate(table, payload):
    if not isinstance(payload, dict): raise HTTPException(400, "payload must be an object")
    unknown = set(payload) - {c.name for c in table.columns}
    if unknown: raise HTTPException(400, f"Unknown column(s): {', '.join(sorted(unknown))}")

def _write_allowed(name):
    if name in READ_ONLY_TABLES: raise HTTPException(403, f"Table '{name}' is read-only")

def _tenant_clause(table, user):
    tenant = table.columns.get("tenant_id")
    tenant_id = user.get("tenant_id")
    if tenant is not None and tenant_id and "platform_admin" not in set(user.get("roles", [])):
        return tenant == str(tenant_id)
    return None

def _where(table, user, *clauses):
    values = [c for c in clauses if c is not None]
    tenant = _tenant_clause(table, user)
    if tenant is not None: values.append(tenant)
    return and_(*values) if values else None

def _audit_table():
    table = Base.metadata.tables.get("admin_audit_log")
    if table is None: raise HTTPException(503, "admin_audit_log migration is required")
    return table

async def _audit(s, actor, action, table_name, record_id, before, after):
    await s.execute(insert(_audit_table()).values(
        id=uuid.uuid4(), actor=actor, action=action, table_name=table_name,
        record_id=str(record_id) if record_id is not None else None,
        before=json.dumps(before, default=str) if before is not None else None,
        after=json.dumps(after, default=str) if after is not None else None,
        created_at=datetime.utcnow(),
    ))

@router.get("/tables")
async def list_tables(user=Depends(require_admin)):
    _platform_admin(user)
    return [{
        "name": name, "read_only": name in READ_ONLY_TABLES,
        "columns": [{"name": c.name, "type": str(c.type), "primary_key": bool(c.primary_key), "nullable": bool(c.nullable)} for c in table.columns],
    } for name, table in sorted(Base.metadata.tables.items())]

@router.get("/tables/{table_name}")
async def list_rows(table_name: str, limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0), search: str | None = Query(None, max_length=200), search_column: str | None = Query(None, max_length=100), sort: str | None = Query(None, max_length=100), descending: bool = False, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user)
    table = _table(table_name)
    cols = {c.name: c for c in table.columns}
    predicate = _tenant_clause(table, user)
    if search:
        if search_column and search_column not in cols: raise HTTPException(400, f"Unknown filter column '{search_column}'")
        target = [cols[search_column]] if search_column else list(table.columns)
        terms = [c.cast(String).ilike(f"%{search}%") for c in target]
        predicate = and_(predicate, or_(*terms)) if predicate is not None else or_(*terms)
    stmt = select(table)
    count = select(func.count()).select_from(table)
    if predicate is not None: stmt = stmt.where(predicate); count = count.where(predicate)
    if sort:
        if sort not in cols: raise HTTPException(400, f"Unknown sort column '{sort}'")
        stmt = stmt.order_by(cols[sort].desc() if descending else cols[sort].asc())
    else:
        pks = list(table.primary_key.columns)
        if pks: stmt = stmt.order_by(pks[0].asc())
    total = int((await s.execute(count)).scalar_one())
    result = await s.execute(stmt.limit(limit).offset(offset))
    return {"table": table_name, "limit": limit, "offset": offset, "total": total, "has_more": offset + limit < total, "rows": [_row_to_dict(r, table) for r in result.fetchall()]}

@router.get("/tables/{table_name}/analysis")
async def analyze_table(table_name: str, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user)
    table = _table(table_name)
    total = int((await s.execute(select(func.count()).select_from(table))).scalar_one())
    return {"table": table_name, "rows": total, "columns": len(table.columns), "primary_key": [c.name for c in table.primary_key.columns], "nullable_columns": [c.name for c in table.columns if c.nullable], "read_only": table_name in READ_ONLY_TABLES}

@router.post("/tables/{table_name}")
async def create_row(table_name: str, payload: dict, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); _write_allowed(table_name)
    table = _table(table_name); _validate(table, payload)
    if table.columns.get("tenant_id") is not None and not payload.get("tenant_id"):
        raise HTTPException(400, "tenant_id is required")
    try:
        row = (await s.execute(insert(table).values(**payload).returning(*table.columns))).fetchone()
        if row is None: raise HTTPException(400, "insert returned no record")
        values = _row_to_dict(row, table); pk = _pk(table)
        await _audit(s, user["sub"], "create", table_name, values.get(pk.name), None, values)
        await s.commit(); return values
    except HTTPException: await s.rollback(); raise
    except Exception as exc: await s.rollback(); raise HTTPException(409, f"create failed: {exc}") from exc

@router.put("/tables/{table_name}/{record_id}")
async def update_row(table_name: str, record_id: str, payload: dict, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); _write_allowed(table_name)
    table = _table(table_name); pk = _pk(table); _validate(table, payload)
    if "tenant_id" in payload: raise HTTPException(400, "tenant_id cannot be changed through generic update")
    where = _where(table, user, pk == record_id)
    try:
        before = (await s.execute(select(table).where(where))).fetchone()
        if before is None: raise HTTPException(404, "Record not found")
        before_values = _row_to_dict(before, table)
        await s.execute(update(table).where(where).values(**payload))
        after = (await s.execute(select(table).where(where))).fetchone()
        after_values = _row_to_dict(after, table)
        await _audit(s, user["sub"], "update", table_name, record_id, before_values, after_values)
        await s.commit(); return after_values
    except HTTPException: await s.rollback(); raise
    except Exception as exc: await s.rollback(); raise HTTPException(409, f"update failed: {exc}") from exc

@router.delete("/tables/{table_name}/{record_id}")
async def delete_row(table_name: str, record_id: str, confirm: bool = False, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); _write_allowed(table_name)
    if not confirm: raise HTTPException(400, "destructive delete requires confirm=true")
    table = _table(table_name); pk = _pk(table); where = _where(table, user, pk == record_id)
    try:
        before = (await s.execute(select(table).where(where))).fetchone()
        if before is None: raise HTTPException(404, "Record not found")
        values = _row_to_dict(before, table)
        await s.execute(delete(table).where(where))
        await _audit(s, user["sub"], "delete", table_name, record_id, values, None)
        await s.commit(); return {"ok": True, "deleted": 1}
    except HTTPException: await s.rollback(); raise
    except Exception as exc: await s.rollback(); raise HTTPException(409, f"delete failed: {exc}") from exc

@router.post("/tables/{table_name}/bulk-delete")
async def bulk_delete(table_name: str, ids: list[str], confirm: bool = False, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); _write_allowed(table_name)
    if not confirm: raise HTTPException(400, "bulk deletion requires confirm=true")
    if not ids or len(ids) > 500: raise HTTPException(400, "ids must contain 1..500 records")
    table = _table(table_name); pk = _pk(table); where = _where(table, user, pk.in_(ids))
    try:
        rows = (await s.execute(select(table).where(where))).fetchall()
        for row in rows:
            values = _row_to_dict(row, table)
            await _audit(s, user["sub"], "bulk_delete", table_name, values.get(pk.name), values, None)
        await s.execute(delete(table).where(where)); await s.commit()
        return {"ok": True, "requested": len(ids), "deleted": len(rows)}
    except HTTPException: await s.rollback(); raise
    except Exception as exc: await s.rollback(); raise HTTPException(409, f"bulk delete failed: {exc}") from exc

@router.get("/tables/{table_name}/export")
async def export_table(table_name: str, format: str = Query("json", pattern="^(json|csv)$"), search: str | None = Query(None, max_length=200), user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user)
    table = _table(table_name); predicate = _tenant_clause(table, user)
    if search:
        terms = [c.cast(String).ilike(f"%{search}%") for c in table.columns]
        predicate = and_(predicate, or_(*terms)) if predicate is not None else or_(*terms)
    stmt = select(table).where(predicate) if predicate is not None else select(table)
    rows = [_row_to_dict(r, table) for r in (await s.execute(stmt.limit(MAX_EXPORT_ROWS))).fetchall()]
    if format == "json":
        body = json.dumps({"table": table_name, "rows": rows}, indent=2, default=str).encode()
        return StreamingResponse(io.BytesIO(body), media_type="application/json", headers={"Content-Disposition": f"attachment; filename={table_name}.json"})
    out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=[c.name for c in table.columns]); writer.writeheader(); writer.writerows(rows)
    return StreamingResponse(io.StringIO(out.getvalue()), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={table_name}.csv"})

@router.post("/tables/{table_name}/import")
async def import_table(table_name: str, file: UploadFile = File(...), user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); _write_allowed(table_name)
    table = _table(table_name)
    if not file.filename or not file.filename.lower().endswith(".csv"): raise HTTPException(400, "CSV import is required")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024: raise HTTPException(413, "CSV exceeds 10 MiB limit")
    try: rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    except Exception as exc: raise HTTPException(400, f"invalid CSV: {exc}") from exc
    if not rows or len(rows) > MAX_IMPORT_ROWS: raise HTTPException(400, f"CSV must contain 1..{MAX_IMPORT_ROWS} data rows")
    valid = {c.name for c in table.columns}; unknown = set((rows[0] if rows else {}).keys()) - valid
    if unknown: raise HTTPException(400, f"Unknown CSV column(s): {', '.join(sorted(unknown))}")
    try:
        pk = _pk(table)
        for payload in rows:
            payload = {k: v for k, v in payload.items() if v != ""}
            _validate(table, payload)
            row = (await s.execute(insert(table).values(**payload).returning(*table.columns))).fetchone()
            values = _row_to_dict(row, table)
            await _audit(s, user["sub"], "import", table_name, values.get(pk.name), None, values)
        await s.commit(); return {"ok": True, "inserted": len(rows), "filename": file.filename}
    except HTTPException: await s.rollback(); raise
    except Exception as exc: await s.rollback(); raise HTTPException(409, f"import rolled back: {exc}") from exc
