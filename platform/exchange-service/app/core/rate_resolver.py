"""Resolve exact, inverse, and USDT-bridged exchange rates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import desc, select

from app.core.db import SessionLocal
from app.core.redis_client import redis_client
from app.models.models import Rate


@dataclass(frozen=True)
class ResolvedRate:
    base: str
    quote: str
    rate: float
    source: str
    fetched_at: str


async def _direct_rate(base: str, quote: str) -> ResolvedRate | None:
    """Return the newest stored exact provider rate."""
    cached = await redis_client.get(f"rate:{base}:{quote}")

    if cached:
        try:
            rate, source, timestamp = cached.split("|", 2)
            return ResolvedRate(
                base=base,
                quote=quote,
                rate=float(rate),
                source=source,
                fetched_at=timestamp,
            )
        except (ValueError, TypeError):
            # Ignore malformed cache entries and fall through to DB.
            pass

    async with SessionLocal() as session:
        result = await session.execute(
            select(Rate)
            .where(Rate.base == base, Rate.quote == quote)
            .order_by(desc(Rate.fetched_at))
            .limit(1)
        )
        row = result.scalar_one_or_none()

    if row is None:
        return None

    timestamp = row.fetched_at.isoformat() if row.fetched_at else datetime.utcnow().isoformat()

    return ResolvedRate(
        base=row.base,
        quote=row.quote,
        rate=float(row.rate),
        source=row.source,
        fetched_at=timestamp,
    )


async def _direct_or_inverse(base: str, quote: str) -> ResolvedRate | None:
    """Resolve an exact pair or its inverse."""
    direct = await _direct_rate(base, quote)
    if direct is not None:
        return direct

    inverse = await _direct_rate(quote, base)
    if inverse is None or inverse.rate == 0:
        return None

    return ResolvedRate(
        base=base,
        quote=quote,
        rate=1.0 / inverse.rate,
        source=f"{inverse.source}-derived",
        fetched_at=inverse.fetched_at,
    )


async def resolve_rate(base: str, quote: str) -> ResolvedRate:
    """
    Resolve a currency pair.

    Resolution order:
      1. identity
      2. exact stored pair
      3. inverse stored pair
      4. USDT bridge using base/USDT and USDT/quote
    """
    base = base.upper().strip()
    quote = quote.upper().strip()

    if not base or not quote:
        raise HTTPException(400, "base and quote are required")

    if base == quote:
        return ResolvedRate(
            base=base,
            quote=quote,
            rate=1.0,
            source="identity",
            fetched_at="1970-01-01T00:00:00",
        )

    # 1/2/3. Exact or inverse.
    resolved = await _direct_or_inverse(base, quote)
    if resolved is not None:
        return resolved

    # 4. Cross through USDT.
    #
    # Example:
    #   USD/USDT = inverse(USDT/USD)
    #   USDT/BDT = exact
    #   USD/BDT = USD/USDT * USDT/BDT
    anchor = "USDT"

    if base != anchor and quote != anchor:
        base_to_anchor = await _direct_or_inverse(base, anchor)
        anchor_to_quote = await _direct_or_inverse(anchor, quote)

        if base_to_anchor is not None and anchor_to_quote is not None:
            return ResolvedRate(
                base=base,
                quote=quote,
                rate=base_to_anchor.rate * anchor_to_quote.rate,
                source=(f"{base_to_anchor.source}+" f"{anchor_to_quote.source}")[:32],
                fetched_at=max(
                    base_to_anchor.fetched_at,
                    anchor_to_quote.fetched_at,
                ),
            )

    raise HTTPException(404, f"no rate for {base}/{quote}")
