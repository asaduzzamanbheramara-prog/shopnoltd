"""Talks to the local exchange-service for FX rates + conversion."""

from datetime import datetime

import httpx
from app.core.config import settings


async def get_rate(frm: str, to: str) -> dict:
    """Get a real FX rate from the internal exchange service.

    Never fabricate a 1.0 rate when the exchange service is unavailable.
    """
    frm = frm.upper().strip()
    to = to.upper().strip()

    if not frm or not to:
        raise ValueError("currency pair is required")

    if frm == to:
        return {
            "rate": 1.0,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "identity",
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(
                f"{settings.exchange_service_url}/api/v1/rates/{frm}/{to}"
            )
            r.raise_for_status()
            data = r.json()

        rate = float(data["rate"])

        if rate <= 0:
            raise RuntimeError(
                f"exchange service returned invalid rate for {frm}/{to}"
            )

        return {
            "rate": rate,
            "timestamp": data.get(
                "fetched_at",
                data.get("timestamp", datetime.utcnow().isoformat()),
            ),
            "source": data.get("source", "exchange-service"),
        }

    except Exception as exc:
        raise RuntimeError(
            f"exchange service unavailable for {frm}/{to}"
        ) from exc




async def convert(frm: str, to: str, amount: float) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{settings.exchange_service_url}/api/v1/convert",
            json={"from": frm, "to": to, "amount": amount},
        )
    r.raise_for_status()
    return r.json()
