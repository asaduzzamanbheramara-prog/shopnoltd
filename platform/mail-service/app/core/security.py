import httpx
from fastapi import HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
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
            algorithms=["RS256"],
            audience=settings.keycloak_audience,
            issuer=settings.keycloak_issuer,
            options={"verify_aud": True, "verify_iss": True},
        )
    except (JWTError, StopIteration):
        raise HTTPException(status_code=401, detail="Invalid or malformed JWT token") from None


async def verify_token_admin(token: str) -> dict:
    u = await verify_token(token)
    roles = u.get("realm_access", {}).get("roles", []) + u.get("resource_access", {}).get(
        settings.keycloak_audience, {}
    ).get("roles", [])
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="admin only")
    return u


# Reuse the Shopnoltd browser OIDC client. The corresponding Keycloak client
# is public and enforces PKCE S256; no client secret is sent to Swagger UI.
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{settings.keycloak_issuer}/protocol/openid-connect/auth",
    tokenUrl=f"{settings.keycloak_issuer}/protocol/openid-connect/token",
    scopes={
        "openid": "OpenID Connect",
        "profile": "Basic profile",
        "email": "Email address",
    },
)
