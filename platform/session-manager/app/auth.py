"""Fail-closed Keycloak JWT authentication for Session Manager APIs."""
import os
from functools import lru_cache
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

bearer = HTTPBearer(auto_error=False)

@lru_cache(maxsize=1)
def _jwks_client():
    issuer = os.getenv("KEYCLOAK_ISSUER", "https://auth.shopnoltd.dpdns.org/realms/shopnoltd")
    url = os.getenv("KEYCLOAK_JWKS_URL", f"{issuer}/protocol/openid-connect/certs")
    if not url:
        raise RuntimeError("KEYCLOAK_JWKS_URL is not configured")
    return PyJWKClient(url, cache_jwk_set=True, lifespan=300)

def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    issuer = os.getenv("KEYCLOAK_ISSUER", "https://auth.shopnoltd.dpdns.org/realms/shopnoltd")
    audience = os.getenv("KEYCLOAK_AUDIENCE", "api-service")
    if not issuer or not audience:
        raise HTTPException(503, "Session Manager authentication is not configured")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    try:
        key = _jwks_client().get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(credentials.credentials, key.key, algorithms=["RS256"], audience=audience, issuer=issuer, options={"require": ["exp", "iat", "sub", "iss", "aud"]})
    except RuntimeError:
        raise HTTPException(503, "Session Manager authentication is not configured")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(401, "Token has no valid subject")
    return {"sub": subject, "username": claims.get("preferred_username")}
