from fastapi import APIRouter, HTTPException
from sqlalchemy import desc, select

from app.core.db import SessionLocal
from app.core.redis_client import redis_client
from app.models.models import Rate
from app.schemas.schemas import RateOut

router = APIRouter()


@router.get("/{base}/{quote}", response_model=RateOut)
async def get_rate(base: str, quote: str):
    base, quote = base.upper(), quote.upper()
    if base == quote:
        return RateOut(
            base=base, quote=quote, rate=1.0, source="identity", fetched_at="1970-01-01T00:00:00"
        )
    cached = await redis_client.get(f"rate:{base}:{quote}")
    if cached:
        rate, src, ts = cached.split("|")
        return RateOut(base=base, quote=quote, rate=float(rate), source=src, fetched_at=ts)
    async with SessionLocal() as s:
        res = await s.execute(
            select(Rate)
            .where(Rate.base == base, Rate.quote == quote)
            .order_by(desc(Rate.fetched_at))
            .limit(1)
        )
        r = res.scalar_one_or_none()
        if not r:
            raise HTTPException(404, f"no rate for {base}/{quote}")
        return RateOut(
            base=r.base,
            quote=r.quote,
            rate=float(r.rate),
            source=r.source,
            fetched_at=r.fetched_at.isoformat(),
        )


@router.get("", response_model=list[RateOut])
async def list_rates(limit: int = 100):
    async with SessionLocal() as s:
        res = await s.execute(select(Rate).order_by(desc(Rate.fetched_at)).limit(limit))
        return [
            RateOut(
                base=r.base,
                quote=r.quote,
                rate=float(r.rate),
                source=r.source,
                fetched_at=r.fetched_at.isoformat(),
            )
            for r in res.scalars().all()
        ]
