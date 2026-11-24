import httpx
import secrets
from fastapi import HTTPException
from shopno_core.security.jwt import JWTError, jwt

from app.core.config import settings

_jwks_cache = None


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
    try:
        h = jwt.get_unverified_header(token)
        keys = await _jwks()
        key = next(k for k in keys["keys"] if k["kid"] == h["kid"])
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.keycloak_audience,
            issuer=settings.keycloak_issuer,
            options={"verify_aud": True, "verify_iss": True},
        )
    except (JWTError, StopIteration) as e:
        raise ValueError(f"invalid token: {e}") from e


async def verify_token_admin(token: str) -> dict:
    if settings.freedomain_internal_key and secrets.compare_digest(token, settings.freedomain_internal_key):
        return {"service": "freedomain-service", "roles": ["service:freedomain"]}

    try:
        u = await verify_token(token)
    except (ValueError, JWTError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    if not ({"admin", "platform_admin"} & (set(u.get("realm_roles") or u.get("roles") or []) | set((u.get("realm_access") or {}).get("roles", []) or []))):
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required",
        )

    return u
