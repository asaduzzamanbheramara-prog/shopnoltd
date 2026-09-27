"""JWT verification via Keycloak JWKS."""

import asyncio

import httpx
from fastapi import HTTPException

from app.core.config import settings
from shopno_core.security.jwt import JWTError, jwt

_jwks_cache = None


async def _jwks():
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    jwks_url = (
        settings.keycloak_jwks_url
        or f"{settings.keycloak_issuer}/protocol/openid-connect/certs"
    )
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

    raise HTTPException(
        status_code=503,
        detail="Unable to reach identity provider; try again shortly",
    ) from last_exc


async def verify_token(token: str) -> dict:
    try:
        unverified = jwt.get_unverified_header(token)
        keys = await _jwks()
        key = next(k for k in keys["keys"] if k["kid"] == unverified["kid"])
        # Accept the service-native audience and the browser/API audience.
        # Audience validation remains enabled in both cases.
        last_error = None
        for audience in (
            settings.keycloak_audience,
            settings.keycloak_web_audience,
        ):
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
    except HTTPException:
        raise
    except (JWTError, StopIteration, ValueError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
