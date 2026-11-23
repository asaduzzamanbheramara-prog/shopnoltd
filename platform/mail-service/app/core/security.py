import httpx
from fastapi import HTTPException
from shopno_core.security.jwt import JWTError, jwt

from app.core.config import settings

_jwks_cache = None


def realm_roles(payload: dict) -> set[str]:
    """Return verified realm-level roles; mail client roles are not platform roles."""
    roles = set(payload.get("realm_roles", []) or [])
    roles.update((payload.get("realm_access") or {}).get("roles", []) or [])
    if "realm_roles" not in payload:
        roles.update(payload.get("roles", []) or [])
    return roles


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
    except (JWTError, StopIteration):
        raise HTTPException(status_code=401, detail="Invalid or malformed JWT token") from None


async def verify_token_admin(token: str) -> dict:
    u = await verify_token(token)
    if not realm_roles(u).intersection({"admin", "platform_admin"}):
        raise HTTPException(status_code=403, detail="admin only")
    return u
