from datetime import datetime

from fastapi import APIRouter

from app.core.db import SessionLocal
from app.core.rate_resolver import resolve_rate
from app.models.models import Conversion
from app.schemas.schemas import ConvertIn, ConvertOut

router = APIRouter()

FEE_PCT = 0.5


@router.post("", response_model=ConvertOut)
async def convert(body: ConvertIn):
    base = body.from_currency.upper().strip()
    quote = body.to_currency.upper().strip()

    resolved = await resolve_rate(base, quote)

    fee = body.amount * FEE_PCT / 100
    net_amount = body.amount - fee
    to_amount = net_amount * resolved.rate

    async with SessionLocal() as session:
        session.add(
            Conversion(
                tenant_id="default",
                user_id=body.user_id or "anonymous",
                from_currency=base,
                to_currency=quote,
                from_amount=body.amount,
                to_amount=to_amount,
                rate=resolved.rate,
                fee=fee,
            )
        )
        await session.commit()

    return ConvertOut(
        from_currency=base,
        to_currency=quote,
        from_amount=body.amount,
        to_amount=to_amount,
        rate=resolved.rate,
        fee=fee,
        source=resolved.source,
        timestamp=datetime.utcnow().isoformat(),
    )
