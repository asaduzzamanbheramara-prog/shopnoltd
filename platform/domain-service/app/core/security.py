import httpx
from fastapi import HTTPException
from shopno_core.security.jwt import JWTError, jwt

from app.core.config import settings

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


async def verify_token_admin(token: str) -> dict:
    try:
        u = await verify_token(token)
    except (ValueError, JWTError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    if "admin" not in u.get("roles", []):
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required",
        )

    return u
