import httpx

from app.core.config import settings


async def pdns_call(method: str, path: str, **kw) -> dict:
    headers = {"X-API-Key": settings.powerdns_key}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.request(method, f"{settings.powerdns_api}{path}", headers=headers, **kw)
    r.raise_for_status()
    return r.json() if r.text else {}
