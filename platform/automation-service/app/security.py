import os

import httpx
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError, jwt

KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", "https://auth.shopnoltd.dpdns.org/realms/shopnoltd").rstrip("/")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "automation-service")
_jwks_cache = None


async def _jwks():
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs")
        response.raise_for_status()
        _jwks_cache = response.json()
    return _jwks_cache


async def current_identity(credentials: HTTPAuthorizationCredentials) -> dict:
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        key = next(k for k in (await _jwks())["keys"] if k["kid"] == header["kid"])
        claims = jwt.decode(token, key, algorithms=[key["alg"]], audience=KEYCLOAK_AUDIENCE, issuer=KEYCLOAK_ISSUER)
    except (JWTError, StopIteration, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"}) from exc
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "token subject unavailable")
    tenant = claims.get("tenant_id") or claims.get("tenantId")
    if not isinstance(tenant, str) or not tenant.strip():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "tenant context unavailable")
    return {"subject": subject, "tenant_id": tenant}
