from fastapi import APIRouter
from sqlalchemy import desc, select

from app.core.db import SessionLocal
from app.core.rate_resolver import resolve_rate
from app.models.models import Rate
from app.schemas.schemas import RateOut

router = APIRouter()


@router.get("/{base}/{quote}", response_model=RateOut)
async def get_rate(base: str, quote: str):
    resolved = await resolve_rate(base, quote)

    return RateOut(
        base=resolved.base,
        quote=resolved.quote,
        rate=resolved.rate,
        source=resolved.source,
        fetched_at=resolved.fetched_at,
    )


@router.get("", response_model=list[RateOut])
async def list_rates(limit: int = 100):
    limit = max(1, min(limit, 500))

    async with SessionLocal() as session:
        result = await session.execute(select(Rate).order_by(desc(Rate.fetched_at)).limit(limit))

        return [
            RateOut(
                base=row.base,
                quote=row.quote,
                rate=float(row.rate),
                source=row.source,
                fetched_at=(row.fetched_at.isoformat() if row.fetched_at else ""),
            )
            for row in result.scalars().all()
        ]
