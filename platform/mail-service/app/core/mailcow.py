import httpx

from app.core.config import settings


async def call_mailcow(action: str, payload: dict) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{settings.mailcow_api_url}/{action}",
            json=payload,
            headers={"X-API-Key": settings.mailcow_api_key},
            timeout=30,
        )
    r.raise_for_status()
    return r.json()
