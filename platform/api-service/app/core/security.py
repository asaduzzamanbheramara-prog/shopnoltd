import logging

import httpx
from fastapi import HTTPException, status
from shopno_core.security.jwt import JWTError, jwt

from app.core.config import settings

_jwks_cache = None
logger = logging.getLogger(__name__)


async def _jwks(force_refresh: bool = False):
    global _jwks_cache
    if force_refresh:
        _jwks_cache = None
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
        key = next((k for k in keys["keys"] if k["kid"] == h["kid"]), None)
        if key is None:
            keys = await _jwks(force_refresh=True)
            key = next((k for k in keys["keys"] if k["kid"] == h["kid"]), None)
        if key is None:
            raise JWTError("Signing key not found")
        return jwt.decode(
            token,
            key,
            algorithms=[key["alg"]],
            audience=settings.keycloak_audience,
            issuer=settings.keycloak_issuer,
            options={"verify_aud": True, "verify_iss": True},
        )
    except (JWTError, StopIteration, KeyError, ValueError) as e:
        logger.warning("JWT validation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def verify_token_admin(token: str) -> dict:
    u = await verify_token(token)
    if "admin" not in u.get("roles", []):
        raise PermissionError("admin only")
    return u
