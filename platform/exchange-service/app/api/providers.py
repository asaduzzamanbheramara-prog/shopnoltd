from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models.models import Rate
from app.schemas.schemas import ProviderOut

router = APIRouter()


@router.get("", response_model=list[ProviderOut])
async def list_providers():
    async with SessionLocal() as s:
        res = await s.execute(
            select(
                Rate.source, func.count(Rate.id).label("c"), func.max(Rate.fetched_at).label("lu")
            ).group_by(Rate.source)
        )
        return [
            ProviderOut(
                name=row[0],
                status="ok",
                last_update=row[2].isoformat() if row[2] else None,
                rates_count=row[1],
            )
            for row in res.all()
        ]
