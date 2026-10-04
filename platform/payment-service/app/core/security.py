"""JWT verification and trusted service authentication."""

import asyncio
import secrets

import httpx
from fastapi import Header, HTTPException

from app.core.config import settings
from shopno_core.security.jwt import JWTError, jwt

_jwks_cache = None


def require_internal_key(x_internal_api_key: str = Header(...)):
    if not settings.internal_api_key:
        raise HTTPException(500, "INTERNAL_API_KEY is not configured; refusing privileged payment operation")
    if not secrets.compare_digest(x_internal_api_key, settings.internal_api_key):
        raise HTTPException(403, "Invalid internal API key")
    return True


async def _jwks():
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    jwks_url = settings.keycloak_jwks_url or f"{settings.keycloak_issuer}/protocol/openid-connect/certs"
    last_exc = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
                _jwks_cache = response.json()
                return _jwks_cache
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))
    raise HTTPException(status_code=503, detail="Unable to reach identity provider; try again shortly") from last_exc


async def verify_token(token: str) -> dict:
    try:
        unverified = jwt.get_unverified_header(token)
        keys = await _jwks()
        key = next(k for k in keys["keys"] if k["kid"] == unverified["kid"])
        last_error = None
        for audience in (settings.keycloak_audience, settings.keycloak_web_audience):
            try:
                claims = jwt.decode(token, key, algorithms=[key["alg"]], audience=audience, options={"verify_aud": True})
                roles = set(claims.get("roles", []) or [])
                roles.update((claims.get("realm_access") or {}).get("roles", []) or [])
                for client in (claims.get("resource_access") or {}).values():
                    roles.update((client or {}).get("roles", []) or [])
                claims["roles"] = sorted(roles)
                return claims
            except JWTError as exc:
                last_error = exc
        raise ValueError(f"invalid token audience: {last_error}")
    except HTTPException:
        raise
    except (JWTError, StopIteration, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"}) from exc
