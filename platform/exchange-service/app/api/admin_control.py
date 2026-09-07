"""Administrative database control surface for exchange-service.

Rates and conversion history are financially/audit sensitive. They are exposed
for inspection and analysis, while direct mutation is prohibited so that the
rate updater remains the single source of truth.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.models import Conversion, Rate
from app.security import require_internal_key

router = APIRouter(
    prefix="/admin/control-plane",
    tags=["exchange-database-control-plane"],
    dependencies=[Depends(require_internal_key)],
)

MODELS = {"rates": Rate, "conversions": Conversion}
READ_ONLY = {"rates", "conversions"}


def _row(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.get("/tables")
async def tables():
    return {
        "service": "exchange-service",
        "database_scope": "exchange",
        "tables": [
            {"name": name, "writable": False, "financially_sensitive": True}
            for name in MODELS
        ],
        "write_policy": "rate and conversion state is service/updater-owned",
    }


@router.get("/tables/{table_name}")
async def list_rows(
    table_name: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    model = MODELS.get(table_name)
    if model is None:
        raise HTTPException(404, f"Unknown exchange table: {table_name}")
    result = await db.execute(select(model).offset(offset).limit(limit))
    rows = result.scalars().all()
    count = await db.execute(select(func.count()).select_from(model))
    total = count.scalar_one()
    return {"table": table_name, "total": total, "offset": offset, "limit": limit, "has_more": offset + len(rows) < total, "rows": [_row(x) for x in rows]}


@router.get("/tables/{table_name}/analysis")
async def analysis(table_name: str, db: AsyncSession = Depends(get_session)):
    model = MODELS.get(table_name)
    if model is None:
        raise HTTPException(404, f"Unknown exchange table: {table_name}")
    count = await db.execute(select(func.count()).select_from(model))
    return {
        "table": table_name,
        "row_count": count.scalar_one(),
        "writable": False,
        "financially_sensitive": True,
        "columns": [
            {"name": c.name, "type": str(c.type), "nullable": c.nullable, "primary_key": c.primary_key}
            for c in model.__table__.columns
        ],
    }


@router.post("/tables/{table_name}")
async def create_row(table_name: str):
    if table_name in READ_ONLY:
        raise HTTPException(403, "Exchange tables are read-only; use the exchange service or rate updater")
    raise HTTPException(404, "Unknown exchange table")


@router.put("/tables/{table_name}/{row_id}")
async def update_row(table_name: str, row_id: str):
    if table_name in READ_ONLY:
        raise HTTPException(403, "Exchange tables are read-only; use the exchange service or rate updater")
    raise HTTPException(404, "Unknown exchange table")


@router.delete("/tables/{table_name}/{row_id}")
async def delete_row(table_name: str, row_id: str):
    if table_name in READ_ONLY:
        raise HTTPException(403, "Exchange tables are read-only; use the exchange service or rate updater")
    raise HTTPException(404, "Unknown exchange table")
