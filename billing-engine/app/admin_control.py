"""Safe billing database control-plane adapter.

The billing database contains money-moving state, so this module deliberately
separates operational CRUD from financial invariants. Wallets, transactions,
ledger entries and audit records are never directly writable here; mutations
must go through the validated billing/ledger APIs.
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, Subscription, Transaction, User, Wallet, WalletLedgerEntry
from app.security import require_internal_key

router = APIRouter(
    prefix="/admin/control-plane",
    tags=["billing-database-control-plane"],
    dependencies=[Depends(require_internal_key)],
)

MODEL_MAP = {
    "users": User,
    "subscriptions": Subscription,
    "wallets": Wallet,
    "transactions": Transaction,
    "wallet_ledger_entries": WalletLedgerEntry,
    "audit_log": AuditLog,
}

# Direct writes are intentionally limited to non-financial operational data.
WRITABLE_TABLES = {"users", "subscriptions"}
READ_ONLY_TABLES = {"wallets", "transactions", "wallet_ledger_entries", "audit_log"}
PROTECTED_FIELDS = {
    "id", "created_at", "updated_at", "balance", "gateway_reference",
    "raw_response", "status", "approved_by", "processed_at", "completed_at",
    "balance_after", "reference", "gateway_token",
}
MAX_LIMIT = 500
MAX_EXPORT = 10000


class RowMutation(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    confirm: bool = False


def _model(table: str):
    if table not in MODEL_MAP:
        raise HTTPException(404, f"Unknown billing table: {table}")
    return MODEL_MAP[table]


def _columns(model) -> dict[str, Any]:
    return {c.key: c for c in inspect(model).columns}


def _serialize(value: Any):
    if isinstance(value, (datetime, Decimal)):
        return str(value)
    return value


def _row(obj):
    return {c.key: _serialize(getattr(obj, c.key)) for c in inspect(obj).mapper.column_attrs}


def _validate_values(table: str, values: dict[str, Any], *, update: bool = False):
    model = _model(table)
    columns = _columns(model)
    unknown = sorted(set(values) - set(columns))
    if unknown:
        raise HTTPException(422, {"unknown_columns": unknown})
    if table not in WRITABLE_TABLES:
        raise HTTPException(403, f"Table '{table}' is read-only; use the billing service API")
    blocked = sorted(set(values) & PROTECTED_FIELDS)
    if blocked:
        raise HTTPException(403, {"protected_fields": blocked})
    for name, value in values.items():
        col = columns[name]
        if value is None and not col.nullable and not update and col.default is None and col.server_default is None:
            raise HTTPException(422, f"Column '{name}' cannot be null")
        if isinstance(value, str) and getattr(col.type, "length", None) and len(value) > col.type.length:
            raise HTTPException(422, f"Column '{name}' exceeds maximum length {col.type.length}")
    return model


def _audit(db: Session, action: str, table: str, row_id: Any, details: dict[str, Any]):
    db.add(AuditLog(action=f"control_plane:{action}", user_id="platform-admin", details=json.dumps({"table": table, "row_id": str(row_id), **details}, default=str)))
    db.commit()


@router.get("/tables")
def tables():
    return {
        "service": "billing-engine",
        "database_scope": "billing",
        "tables": [
            {"name": name, "writable": name in WRITABLE_TABLES, "financially_sensitive": name in READ_ONLY_TABLES}
            for name in MODEL_MAP
        ],
        "write_policy": "financial state is service-API-only",
    }


@router.get("/tables/{table_name}")
def list_rows(
    table_name: str,
    limit: int = Query(50, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    search: str | None = None,
    sort: str | None = None,
    descending: bool = False,
    db: Session = Depends(get_db),
):
    model = _model(table_name)
    columns = _columns(model)
    query = db.query(model)
    if search:
        text_columns = [c for c in columns.values() if getattr(c.type, "python_type", None) is str]
        if text_columns:
            from sqlalchemy import or_
            query = query.filter(or_(*[c.ilike(f"%{search}%") for c in text_columns]))
    if sort:
        if sort not in columns:
            raise HTTPException(422, f"Unknown sort column: {sort}")
        query = query.order_by(columns[sort].desc() if descending else columns[sort].asc())
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    return {"table": table_name, "total": total, "offset": offset, "limit": limit, "has_more": offset + len(rows) < total, "rows": [_row(x) for x in rows]}


@router.get("/tables/{table_name}/analysis")
def analyze(table_name: str, db: Session = Depends(get_db)):
    model = _model(table_name)
    columns = _columns(model)
    total = db.query(model).count()
    return {
        "table": table_name,
        "row_count": total,
        "columns": [
            {"name": c.key, "type": str(c.type), "nullable": c.nullable, "primary_key": c.primary_key}
            for c in columns.values()
        ],
        "writable": table_name in WRITABLE_TABLES,
        "financially_sensitive": table_name in READ_ONLY_TABLES,
    }


@router.post("/tables/{table_name}")
def create_row(table_name: str, mutation: RowMutation, db: Session = Depends(get_db)):
    if not mutation.confirm:
        raise HTTPException(400, "confirm=true is required")
    model = _validate_values(table_name, mutation.values)
    try:
        obj = model(**mutation.values)
        db.add(obj)
        db.commit()
        db.refresh(obj)
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, "Row could not be created; check required, unique and foreign-key constraints") from exc
    _audit(db, "create", table_name, getattr(obj, "id", "unknown"), {"fields": sorted(mutation.values)})
    return _row(obj)


@router.put("/tables/{table_name}/{row_id}")
def update_row(table_name: str, row_id: str, mutation: RowMutation, db: Session = Depends(get_db)):
    if not mutation.confirm:
        raise HTTPException(400, "confirm=true is required")
    model = _validate_values(table_name, mutation.values, update=True)
    obj = db.get(model, row_id)
    if not obj:
        raise HTTPException(404, "Row not found")
    try:
        for key, value in mutation.values.items():
            setattr(obj, key, value)
        db.commit()
        db.refresh(obj)
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, "Row could not be updated; check constraints") from exc
    _audit(db, "update", table_name, row_id, {"fields": sorted(mutation.values)})
    return _row(obj)


@router.delete("/tables/{table_name}/{row_id}")
def delete_row(table_name: str, row_id: str, confirm: bool = False, db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(400, "confirm=true is required")
    if table_name not in WRITABLE_TABLES:
        raise HTTPException(403, f"Table '{table_name}' is read-only; use the billing service API")
    model = _model(table_name)
    obj = db.get(model, row_id)
    if not obj:
        raise HTTPException(404, "Row not found")
    try:
        db.delete(obj)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, "Row could not be deleted; dependent records may exist") from exc
    _audit(db, "delete", table_name, row_id, {})
    return {"deleted": True, "id": row_id}


@router.get("/export/{table_name}")
def export_rows(table_name: str, format: str = Query("json", pattern="^(json|csv)$"), db: Session = Depends(get_db)):
    model = _model(table_name)
    rows = db.query(model).limit(MAX_EXPORT).all()
    data = [_row(x) for x in rows]
    if format == "json":
        return {"table": table_name, "format": "json", "rows": data, "truncated": len(rows) == MAX_EXPORT}
    import csv
    from io import StringIO
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=list(_columns(model)))
    writer.writeheader()
    writer.writerows(data)
    return {"table": table_name, "format": "csv", "content": out.getvalue(), "truncated": len(rows) == MAX_EXPORT}
