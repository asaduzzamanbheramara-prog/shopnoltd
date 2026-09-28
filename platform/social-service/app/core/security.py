import httpx
import os
from shopno_core.security.jwt import JWTError, jwt

from app.core.config import settings

_jwks_cache = None
AUTOMATION_TOKEN = os.getenv("SHOPNOLTD_INTERNAL_AUTOMATION_TOKEN", "")


async def _jwks():
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient() as c:
        jwks_url = settings.keycloak_jwks_url or f"{settings.keycloak_issuer}/protocol/openid-connect/certs"
        r = await c.get(jwks_url)
        r.raise_for_status()
        _jwks_cache = r.json()
    return _jwks_cache


async def verify_token(token: str) -> dict:
    if AUTOMATION_TOKEN and token == AUTOMATION_TOKEN:
        return {"sub": "n8n-automation", "tenant_id": "default", "automation": True}
    try:
        h = jwt.get_unverified_header(token)
        keys = await _jwks()
        key = next(k for k in keys["keys"] if k["kid"] == h["kid"])
        return jwt.decode(
            token,
            key,
            algorithms=[key["alg"]],
            audience=settings.keycloak_audience,
            options={"verify_aud": True},
        )
    except (JWTError, StopIteration) as e:
        raise ValueError(f"invalid token: {e}") from e
