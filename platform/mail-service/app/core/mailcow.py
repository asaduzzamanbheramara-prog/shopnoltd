import httpx

from app.core.config import settings


def _configured_api_key() -> str:
    key = settings.mailcow_api_key.strip()
    if not key or key.lower().startswith("change_me") or key.lower() in {"placeholder", "changeme", "your_api_key"}:
        raise RuntimeError("Mailcow API key is not configured")
    return key


async def call_mailcow(action: str, payload: dict) -> object:
    api_key = _configured_api_key()
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{settings.mailcow_api_url}/{action}",
            json=payload,
            headers={"X-API-Key": api_key},
            timeout=30,
        )
    r.raise_for_status()
    return r.json()
