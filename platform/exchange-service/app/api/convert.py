from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import desc, select

from app.core.db import SessionLocal
from app.models.models import Conversion, Rate
from app.schemas.schemas import ConvertIn, ConvertOut

router = APIRouter()
FEE_PCT = 0.5


async def _resolve_rate(base: str, quote: str) -> tuple[float, str]:
    if base == quote:
        return 1.0, "identity"
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
        return float(r.rate), r.source


@router.post("", response_model=ConvertOut)
async def convert(body: ConvertIn):
    rate, src = await _resolve_rate(body.from_currency.upper(), body.to_currency.upper())
    fee = body.amount * FEE_PCT / 100
    to_amount = (body.amount - fee) * rate
    async with SessionLocal() as s:
        s.add(
            Conversion(
                tenant_id="default",
                user_id=body.user_id or "anonymous",
                from_currency=body.from_currency.upper(),
                to_currency=body.to_currency.upper(),
                from_amount=body.amount,
                to_amount=to_amount,
                rate=rate,
                fee=fee,
            )
        )
        await s.commit()
    return ConvertOut(
        from_currency=body.from_currency.upper(),
        to_currency=body.to_currency.upper(),
        from_amount=body.amount,
        to_amount=to_amount,
        rate=rate,
        fee=fee,
        source=src,
        timestamp=datetime.utcnow().isoformat(),
    )
