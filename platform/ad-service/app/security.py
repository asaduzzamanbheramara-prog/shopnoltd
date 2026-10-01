import time
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

bearer = HTTPBearer()
_jwks: dict[str, Any] | None = None
_jwks_at = 0.0


async def _get_jwks() -> dict[str, Any]:
    global _jwks, _jwks_at
    if _jwks and time.time() - _jwks_at < 300:
        return _jwks
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(settings.keycloak_jwks_url)
        response.raise_for_status()
        _jwks = response.json()
        _jwks_at = time.time()
        return _jwks


async def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict[str, Any]:
    try:
        token = credentials.credentials
        header = jwt.get_unverified_header(token)
        keys = await _get_jwks()
        key = next(k for k in keys["keys"] if k["kid"] == header["kid"])
        claims = jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "RS256")],
            audience=settings.keycloak_audience,
            issuer=settings.keycloak_issuer,
        )
        subject = claims.get("sub")
        if not subject:
            raise ValueError("missing subject")
        return claims
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def is_admin(user: dict[str, Any]) -> bool:
    return bool(set(user.get("roles", [])) & {"admin", "platform_admin"})


async def require_admin(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
