import httpx
from shopno_core.security.jwt import JWTError, jwt

from app.core.config import settings

_jwks_cache = None
ACCEPTED_AUDIENCES = ("analytics-service", "api-service")


async def _jwks(force_refresh: bool = False):
    global _jwks_cache
    if force_refresh:
        _jwks_cache = None
    if _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(settings.keycloak_jwks_url)
        r.raise_for_status()
        _jwks_cache = r.json()
    return _jwks_cache


async def verify_token(token: str) -> dict:
    try:
        h = jwt.get_unverified_header(token)
        unverified_claims = jwt.get_unverified_claims(token)
        keys = await _jwks()
        key = next((k for k in keys["keys"] if k["kid"] == h["kid"]), None)
        if key is None:
            keys = await _jwks(force_refresh=True)
            key = next((k for k in keys["keys"] if k["kid"] == h["kid"]), None)
        if key is None:
            raise JWTError("Signing key not found")
        last_error = None
        for audience in ACCEPTED_AUDIENCES:
            try:
                return jwt.decode(token, key, algorithms=[key["alg"]], audience=audience,
                                  issuer=settings.keycloak_issuer,
                                  options={"verify_aud": True, "verify_iss": True})
            except JWTError as exc:
                last_error = exc
        raise JWTError(f"invalid token audience: {last_error}")
    except Exception as e:
        raise ValueError(f"invalid token: kid={locals().get('h', {}).get('kid')} aud={locals().get('unverified_claims', {}).get('aud')} error={e}") from e


async def verify_token_admin(token: str) -> dict:
    u = await verify_token(token)
    roles = set(u.get("roles", []))
    roles.update((u.get("realm_access") or {}).get("roles", []) or [])
    for client in (u.get("resource_access") or {}).values():
        roles.update((client or {}).get("roles", []) or [])
    if not roles.intersection({"admin", "platform_admin"}):
        raise PermissionError("admin only")
    u["roles"] = sorted(roles)
    return u
