"""Periodically pull rates from multiple sources and store in DB + cache."""

import asyncio
from datetime import datetime

import httpx
import structlog

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.redis_client import redis_client
from app.models.models import Rate

log = structlog.get_logger()


class RateUpdater:
    def __init__(self):
        self._task = None
        self._running = False

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while self._running:
            try:
                await self._pull_all()
            except Exception as e:
                log.exception("rate.update.failed", err=str(e))
            await asyncio.sleep(settings.rate_refresh_seconds)

    async def _pull_all(self):
        results = await asyncio.gather(
            self._pull_binance(),
            self._pull_coingecko(),
            self._pull_openexchangerates(),
            return_exceptions=True,
        )

        rates = []
        for result in results:
            if isinstance(result, Exception):
                log.warning("rate.source.failed", err=str(result))
                continue
            rates.extend(result)

        async with SessionLocal() as s:
            for base, quote, rate, source in rates:
                r = Rate(
                    base=base, quote=quote, rate=rate, source=source, fetched_at=datetime.utcnow()
                )
                s.add(r)
                await redis_client.set(
                    f"rate:{base}:{quote}",
                    f"{rate}|{source}|{datetime.utcnow().isoformat()}",
                    ex=600,
                )
            await s.commit()

    async def _pull_binance(self) -> list:
        out = []
        for c in settings.crypto_list:
            try:
                async with httpx.AsyncClient() as cli:
                    r = await cli.get(
                        f"{settings.binance_api}/api/v3/ticker/price",
                        params={"symbol": f"{c}USDT"},
                        timeout=10,
                    )
                d = r.json()
                if "price" in d:
                    out.append((c, "USDT", float(d["price"]), "binance"))
                    out.append(("USDT", c, 1.0 / float(d["price"]), "binance"))
            except Exception as e:
                log.warning("binance.fetch.failed", coin=c, err=str(e))
        return out

    async def _pull_coingecko(self) -> list:
        out = []
        try:
            ids = {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "USDT": "tether",
                "BNB": "binancecoin",
                "SOL": "solana",
                "TRX": "tron",
                "XRP": "ripple",
                "ADA": "cardano",
                "DOGE": "dogecoin",
                "USDC": "usd-coin",
            }
            vs = ",".join(settings.fiat_list).lower()
            async with httpx.AsyncClient() as cli:
                r = await cli.get(
                    f"{settings.coingecko_api}/simple/price",
                    params={"ids": ",".join(ids.values()), "vs_currencies": vs},
                    timeout=15,
                )
            d = r.json()
            for sym, cid in ids.items():
                for fiat, val in d.get(cid, {}).items():
                    out.append((sym, fiat.upper(), float(val), "coingecko"))
        except Exception as e:
            log.warning("coingecko.fetch.failed", err=str(e))
        return out

    async def _pull_openexchangerates(self) -> list:
        if not settings.openexchangerates_app_id:
            return []
        out = []
        try:
            async with httpx.AsyncClient() as cli:
                r = await cli.get(
                    f"https://openexchangerates.org/api/latest.json?app_id={settings.openexchangerates_app_id}",
                    timeout=10,
                )
            d = r.json().get("rates", {})
            for f in settings.fiat_list:
                if f != "USD" and f in d:
                    out.append((f, "USD", float(d[f]), "openexchangerates"))
                    out.append(("USD", f, 1.0 / float(d[f]), "openexchangerates"))
        except Exception as e:
            log.warning("openexchangerates.fetch.failed", err=str(e))
        return out
