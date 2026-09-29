import httpx
from shopno_core.security.jwt import JWTError, jwt

from app.core.config import settings

_jwks_cache = None
ACCEPTED_AUDIENCES = ("storage-service", "api-service")


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
        last_error = None
        for audience in ACCEPTED_AUDIENCES:
            try:
                return jwt.decode(
                    token,
                    key,
                    algorithms=[key["alg"]],
                    audience=audience,
                    options={"verify_aud": True},
                )
            except JWTError as exc:
                last_error = exc
        raise ValueError(f"invalid token audience: {last_error}")
    except (JWTError, StopIteration) as e:
        raise ValueError(f"invalid token: {e}") from e


async def verify_token_admin(token: str) -> dict:
    u = await verify_token(token)
    roles = set(u.get("roles", [])) | set(u.get("realm_access", {}).get("roles", []))
    if not roles.intersection({"admin", "platform_admin"}):
        raise PermissionError("admin only")
    return u
