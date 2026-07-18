"""Talks to the local exchange-service for FX rates + conversion."""

from datetime import datetime

import httpx
from app.core.config import settings


async def get_rate(frm: str, to: str) -> dict:
    if frm == to:
        return {"rate": 1.0, "timestamp": datetime.utcnow().isoformat()}
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{settings.exchange_service_url}/api/v1/rates/{frm}/{to}")
    r.raise_for_status()
    return r.json()


async def convert(frm: str, to: str, amount: float) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{settings.exchange_service_url}/api/v1/convert",
            json={"from": frm, "to": to, "amount": amount},
        )
    r.raise_for_status()
    return r.json()
