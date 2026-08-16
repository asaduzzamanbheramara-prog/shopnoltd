from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.models import Conversion
from app.schemas.schemas import ConvertOut

router = APIRouter()


@router.get("/{user_id}", response_model=list[ConvertOut])
async def history(user_id: str, limit: int = Query(50, le=200)):
    async with SessionLocal() as s:
        res = await s.execute(
            select(Conversion)
            .where(Conversion.user_id == user_id)
            .order_by(Conversion.created_at.desc())
            .limit(limit)
        )
        return [
            ConvertOut(
                from_currency=c.from_currency,
                to_currency=c.to_currency,
                from_amount=float(c.from_amount),
                to_amount=float(c.to_amount),
                rate=float(c.rate),
                fee=float(c.fee),
                source="history",
                timestamp=c.created_at.isoformat(),
            )
            for c in res.scalars().all()
        ]
