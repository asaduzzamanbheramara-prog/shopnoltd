"""High-privilege payment database control-plane API.

The payment database is financially sensitive. Generic CRUD/import is therefore
closed for all current payment tables; money-moving changes must go through the
validated payment/billing APIs. This module provides safe discovery, analysis,
search, export and reporting without exposing arbitrary SQL.
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
from sqlalchemy import String, and_, func, insert, or_, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.sqltypes import Boolean, Date, DateTime, Enum, Float, Integer, Numeric, String as SAString

router = APIRouter()
READ_ONLY_TABLES = {"wallets", "transactions", "webhook_events", "admin_audit_log", "alembic_version"}
WRITABLE_TABLES: set[str] = set()
MAX_PAGE_SIZE = 500
MAX_IMPORT_ROWS = 5000
MAX_EXPORT_ROWS = 10000
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

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

def _write_allowed(name):
    _table(name)
    if name not in WRITABLE_TABLES:
        raise HTTPException(403, f"Table '{name}' is read-only through the generic control plane; use its validated service API")

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

def _column_meta(column):
    result = {"name": column.name, "type": str(column.type), "nullable": bool(column.nullable), "primary_key": bool(column.primary_key), "default": bool(column.default or column.server_default)}
    if isinstance(column.type, SAString) and column.type.length: result["max_length"] = column.type.length
    if isinstance(column.type, Enum): result["enum_values"] = list(column.type.enums)
    return result

def _convert_value(column, value):
    if value is None or value == "": return None
    typ = column.type
    try:
        if isinstance(typ, SAString):
            text = str(value)
            if typ.length and len(text) > typ.length: raise ValueError(f"exceeds max length {typ.length}")
            return text
        if isinstance(typ, UUID): return uuid.UUID(str(value))
        if isinstance(typ, Numeric): return Decimal(str(value))
        if isinstance(typ, Integer): return int(value)
        if isinstance(typ, Float): return float(value)
        if isinstance(typ, Boolean):
            if isinstance(value, bool): return value
            text = str(value).strip().lower()
            if text in {"true", "1", "yes", "y"}: return True
            if text in {"false", "0", "no", "n"}: return False
            raise ValueError("expected boolean")
        if isinstance(typ, DateTime):
            if isinstance(value, datetime): return value
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if isinstance(typ, Date):
            if isinstance(value, date) and not isinstance(value, datetime): return value
            return date.fromisoformat(str(value))
        if isinstance(typ, Enum):
            text = str(value)
            if text not in typ.enums: raise ValueError(f"must be one of {typ.enums}")
            return text
        if hasattr(typ, "python_type") and typ.python_type in (dict, list):
            if isinstance(value, (dict, list)): return value
            return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {typ}: {exc}") from exc
    return value

def _validate_payload(table, payload, *, partial=False):
    if not isinstance(payload, dict): raise HTTPException(400, "payload must be an object")
    valid = {c.name for c in table.columns}
    unknown = set(payload) - valid
    if unknown: raise HTTPException(400, f"Unknown column(s): {', '.join(sorted(unknown))}")
    converted = {}
    for column in table.columns:
        if column.name not in payload:
            if not partial and not column.nullable and not column.primary_key and not column.default and not column.server_default:
                raise HTTPException(400, f"Missing required column '{column.name}'")
            continue
        try: converted[column.name] = _convert_value(column, payload[column.name])
        except ValueError as exc: raise HTTPException(400, f"Invalid column '{column.name}': {exc}") from exc
        if converted[column.name] is None and not column.nullable and not column.primary_key:
            raise HTTPException(400, f"Column '{column.name}' cannot be null")
    return converted

def _unique_constraints(table):
    constraints = []
    for constraint in table.constraints:
        cols = [c.name for c in getattr(constraint, "columns", [])]
        if getattr(constraint, "unique", False) and cols: constraints.append(cols)
    for index in table.indexes:
        cols = [c.name for c in index.columns]
        if index.unique and cols: constraints.append(cols)
    return constraints

def _raise_integrity(exc, action):
    detail = str(getattr(exc, "orig", exc)).lower()
    if "unique" in detail or "duplicate" in detail: raise HTTPException(409, f"{action} rejected: duplicate value violates a unique constraint") from exc
    if "foreign key" in detail: raise HTTPException(409, f"{action} rejected: referenced record does not exist") from exc
    if "not-null" in detail or "null value" in detail: raise HTTPException(400, f"{action} rejected: required value is missing") from exc
    raise HTTPException(409, f"{action} rejected by database constraint") from exc

@router.get("/tables")
async def list_tables(user=Depends(require_admin)):
    _platform_admin(user)
    return [{"name": name, "read_only": name not in WRITABLE_TABLES, "writable": name in WRITABLE_TABLES, "financially_sensitive": name in READ_ONLY_TABLES, "columns": [_column_meta(c) for c in table.columns], "unique_constraints": _unique_constraints(table)} for name, table in sorted(Base.metadata.tables.items())]

@router.get("/tables/{table_name}")
async def list_rows(table_name: str, limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0), search: str | None = Query(None, max_length=200), search_column: str | None = Query(None, max_length=100), sort: str | None = Query(None, max_length=100), descending: bool = False, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); table = _table(table_name); cols = {c.name: c for c in table.columns}; predicate = _tenant_clause(table, user)
    if search:
        if search_column and search_column not in cols: raise HTTPException(400, f"Unknown filter column '{search_column}'")
        target = [cols[search_column]] if search_column else list(table.columns); terms = [c.cast(String).ilike(f"%{search}%") for c in target]
        predicate = and_(predicate, or_(*terms)) if predicate is not None else or_(*terms)
    stmt = select(table); count = select(func.count()).select_from(table)
    if predicate is not None: stmt = stmt.where(predicate); count = count.where(predicate)
    if sort:
        if sort not in cols: raise HTTPException(400, f"Unknown sort column '{sort}'")
        stmt = stmt.order_by(cols[sort].desc() if descending else cols[sort].asc())
    else:
        pks = list(table.primary_key.columns)
        if pks: stmt = stmt.order_by(pks[0].asc())
    total = int((await s.execute(count)).scalar_one()); result = await s.execute(stmt.limit(limit).offset(offset))
    return {"table": table_name, "limit": limit, "offset": offset, "total": total, "has_more": offset + limit < total, "rows": [_row_to_dict(r, table) for r in result.fetchall()]}

@router.get("/tables/{table_name}/analysis")
async def analyze_table(table_name: str, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); table = _table(table_name); total = int((await s.execute(select(func.count()).select_from(table))).scalar_one())
    return {"table": table_name, "rows": total, "columns": len(table.columns), "primary_key": [c.name for c in table.primary_key.columns], "nullable_columns": [c.name for c in table.columns if c.nullable], "read_only": table_name not in WRITABLE_TABLES, "financially_sensitive": table_name in READ_ONLY_TABLES, "column_metadata": [_column_meta(c) for c in table.columns], "unique_constraints": _unique_constraints(table)}

@router.post("/tables/{table_name}")
async def create_row(table_name: str, payload: dict, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); _write_allowed(table_name); table = _table(table_name); payload = _validate_payload(table, payload)
    try:
        row = (await s.execute(insert(table).values(**payload).returning(*table.columns))).fetchone()
        if row is None: raise HTTPException(400, "insert returned no record")
        values = _row_to_dict(row, table); await _audit(s, user["sub"], "create", table_name, values.get(_pk(table).name), None, values); await s.commit(); return values
    except HTTPException: await s.rollback(); raise
    except IntegrityError as exc: await s.rollback(); _raise_integrity(exc, "create")

@router.put("/tables/{table_name}/{record_id}")
async def update_row(table_name: str, record_id: str, payload: dict, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); _write_allowed(table_name); table = _table(table_name); pk = _pk(table); payload = _validate_payload(table, payload, partial=True)
    if not payload: raise HTTPException(400, "No fields supplied for update")
    if any(k in payload for k in {pk.name, "tenant_id", "created_at", "updated_at"}): raise HTTPException(400, "identity, tenant, and timestamp fields cannot be changed through generic update")
    where = _where(table, user, pk == record_id)
    try:
        before = (await s.execute(select(table).where(where))).fetchone()
        if before is None: raise HTTPException(404, "Record not found")
        before_values = _row_to_dict(before, table)
        for cols in _unique_constraints(table):
            if any(c not in payload for c in cols): continue
            predicate = and_(*(table.columns[c] == payload[c] for c in cols), pk != record_id)
            if _tenant_clause(table, user) is not None: predicate = and_(predicate, _tenant_clause(table, user))
            if (await s.execute(select(func.count()).select_from(table).where(predicate))).scalar_one(): raise HTTPException(409, f"update rejected: duplicate value for unique fields {cols}")
        await s.execute(table.update().where(where).values(**payload)); after = (await s.execute(select(table).where(where))).fetchone(); after_values = _row_to_dict(after, table)
        await _audit(s, user["sub"], "update", table_name, record_id, before_values, after_values); await s.commit(); return after_values
    except HTTPException: await s.rollback(); raise
    except IntegrityError as exc: await s.rollback(); _raise_integrity(exc, "update")

@router.delete("/tables/{table_name}/{record_id}")
async def delete_row(table_name: str, record_id: str, confirm: bool = False, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); _write_allowed(table_name)
    if not confirm: raise HTTPException(400, "destructive delete requires confirm=true")
    raise HTTPException(403, "Generic deletion is disabled for payment entities; use the validated service workflow")

@router.post("/tables/{table_name}/bulk-delete")
async def bulk_delete(table_name: str, ids: list[str], confirm: bool = False, user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); _write_allowed(table_name)
    if not confirm: raise HTTPException(400, "bulk deletion requires confirm=true")
    raise HTTPException(403, "Generic bulk deletion is disabled for payment entities; use the validated service workflow")

async def _filtered_rows(table, search, user, s):
    predicate = _tenant_clause(table, user)
    if search:
        terms = [c.cast(String).ilike(f"%{search}%") for c in table.columns]; predicate = and_(predicate, or_(*terms)) if predicate is not None else or_(*terms)
    stmt = select(table)
    if predicate is not None: stmt = stmt.where(predicate)
    rows = [_row_to_dict(r, table) for r in (await s.execute(stmt.limit(MAX_EXPORT_ROWS + 1))).fetchall()]
    return rows[:MAX_EXPORT_ROWS], len(rows) > MAX_EXPORT_ROWS

@router.get("/tables/{table_name}/export")
async def export_table(table_name: str, format: str = Query("json", pattern="^(json|csv|xlsx)$"), search: str | None = Query(None, max_length=200), user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); table = _table(table_name); rows, truncated = await _filtered_rows(table, search, user, s); filename = table_name
    if format == "json":
        body = json.dumps({"table": table_name, "rows": rows, "truncated": truncated}, indent=2, default=str).encode(); return StreamingResponse(io.BytesIO(body), media_type="application/json", headers={"Content-Disposition": f"attachment; filename={filename}.json"})
    if format == "csv":
        out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=[c.name for c in table.columns]); writer.writeheader(); writer.writerows(rows); return StreamingResponse(io.StringIO(out.getvalue()), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}.csv"})
    try:
        from openpyxl import Workbook
        from openpyxl.utils import get_column_letter
        wb = Workbook(); ws = wb.active; ws.title = table_name[:31]; headers = [c.name for c in table.columns]; ws.append(headers)
        for row in rows: ws.append([row.get(h) for h in headers])
        for idx, header in enumerate(headers, 1): ws.column_dimensions[get_column_letter(idx)].width = min(max(len(header) + 2, 12), 40)
        output = io.BytesIO(); wb.save(output); output.seek(0); return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"})
    except ImportError as exc: raise HTTPException(503, "XLSX support is not installed") from exc

async def _read_import(file: UploadFile):
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES: raise HTTPException(413, "import file exceeds 10 MiB limit")
    name = (file.filename or "").lower()
    try:
        if name.endswith(".csv"): return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        if name.endswith(".json"):
            payload = json.loads(raw.decode("utf-8")); payload = payload.get("rows", payload.get("data")) if isinstance(payload, dict) else payload
            if not isinstance(payload, list) or not all(isinstance(r, dict) for r in payload): raise ValueError("JSON must be an array of objects or an object containing rows/data")
            return payload
        if name.endswith(".xlsx"):
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True); values = list(wb.active.iter_rows(values_only=True))
            if not values: return []
            headers = [str(v) if v is not None else "" for v in values[0]]
            if any(not h for h in headers): raise ValueError("XLSX contains an empty header")
            return [dict(zip(headers, row)) for row in values[1:] if any(v is not None for v in row)]
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc: raise HTTPException(400, f"invalid import file: {exc}") from exc
    except ImportError as exc: raise HTTPException(503, "XLSX support is not installed") from exc
    raise HTTPException(400, "supported import formats are CSV, JSON, and XLSX")

@router.post("/tables/{table_name}/import")
async def import_table(table_name: str, file: UploadFile = File(...), user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); _write_allowed(table_name); table = _table(table_name); rows = await _read_import(file)
    if not rows or len(rows) > MAX_IMPORT_ROWS: raise HTTPException(400, f"import must contain 1..{MAX_IMPORT_ROWS} data rows")
    try:
        converted_rows = [_validate_payload(table, dict(raw)) for raw in rows]
        for cols in _unique_constraints(table):
            seen = set()
            for row in converted_rows:
                key = tuple(row.get(c) for c in cols)
                if None not in key and key in seen: raise HTTPException(409, f"import contains duplicate unique key {cols}: {key}")
                if None not in key: seen.add(key)
            for row in converted_rows:
                if any(c not in row for c in cols): continue
                predicate = and_(*(table.columns[c] == row[c] for c in cols)); tenant = _tenant_clause(table, user)
                if tenant is not None: predicate = and_(predicate, tenant)
                if (await s.execute(select(func.count()).select_from(table).where(predicate))).scalar_one(): raise HTTPException(409, f"import conflicts with existing unique key {cols}")
        inserted = []
        for payload in converted_rows:
            row = (await s.execute(insert(table).values(**payload).returning(*table.columns))).fetchone(); values = _row_to_dict(row, table); inserted.append(values); await _audit(s, user["sub"], "import", table_name, values.get(_pk(table).name), None, values)
        await s.commit(); return {"ok": True, "inserted": len(inserted), "filename": file.filename, "format": (file.filename or "").rsplit(".", 1)[-1].lower()}
    except HTTPException: await s.rollback(); raise
    except IntegrityError as exc: await s.rollback(); _raise_integrity(exc, "import")

@router.get("/tables/{table_name}/report")
async def report_table(table_name: str, format: str = Query("pdf", pattern="^pdf$"), search: str | None = Query(None, max_length=200), user=Depends(require_admin), s: AsyncSession = Depends(db)):
    _platform_admin(user); table = _table(table_name); rows, truncated = await _filtered_rows(table, search, user, s)
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc: raise HTTPException(503, "PDF reporting support is not installed") from exc
    output = io.BytesIO(); doc = SimpleDocTemplate(output, pagesize=landscape(letter), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24); styles = getSampleStyleSheet()
    story = [Paragraph(f"Shopnoltd Database Report — {table_name}", styles["Title"]), Spacer(1, 0.15 * inch), Paragraph(f"Rows shown: {len(rows)}; truncated: {truncated}; writable: {table_name in WRITABLE_TABLES}", styles["Normal"]), Spacer(1, 0.15 * inch)]
    headers = [c.name for c in table.columns]; data = [headers] + [[str(row.get(h, ""))[:80] for h in headers] for row in rows[:200]]
    if data:
        tbl = Table(data, repeatRows=1); tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 6), ("VALIGN", (0, 0), (-1, -1), "TOP")])); story.append(tbl)
    doc.build(story); output.seek(0); return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={table_name}-report.pdf"})
