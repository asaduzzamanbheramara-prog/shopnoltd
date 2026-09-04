"""JWT verification via Keycloak JWKS."""

import httpx
from app.core.config import settings
from fastapi import HTTPException
from shopno_core.security.jwt import JWTError, jwt

_jwks_cache = None


async def _jwks():
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{settings.keycloak_issuer}/protocol/openid-connect/certs")
        r.raise_for_status()
        _jwks_cache = r.json()
    return _jwks_cache


async def verify_token(token: str) -> dict:
    try:
        unverified = jwt.get_unverified_header(token)
        keys = await _jwks()
        key = next(k for k in keys["keys"] if k["kid"] == unverified["kid"])
        return jwt.decode(
            token,
            key,
            algorithms=[key["alg"]],
            audience=settings.keycloak_audience,
            options={"verify_aud": True},
        )
    except (JWTError, StopIteration, KeyError, httpx.HTTPError) as exc:
        raise ValueError(f"invalid authentication token: {exc}") from exc


async def verify_token_admin(token: str) -> dict:
    try:
        user = await verify_token(token)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    roles = user.get("roles", [])
    if "platform_admin" not in roles and "admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
