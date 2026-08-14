import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from shopno_core.security.jwt import JWTError, jwt

from app.core.config import settings

_jwks_cache = None
bearer = HTTPBearer(auto_error=True)


def _fernet() -> Fernet:
    key = settings.ai_key_encryption_key
    if not key:
        raise RuntimeError(
            "AI_KEY_ENCRYPTION_KEY is not configured; "
            "refusing to encrypt/decrypt provider credentials"
        )

    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise RuntimeError("AI_KEY_ENCRYPTION_KEY is not a valid Fernet key") from exc


def encrypt_secret(value: str) -> str:
    if not value:
        raise ValueError("Cannot encrypt an empty secret")
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    if not value:
        raise ValueError("Cannot decrypt an empty secret")

    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Unable to decrypt provider credential; "
            "the configured AI_KEY_ENCRYPTION_KEY may not match the key "
            "used to encrypt the stored credential"
        ) from exc


def mask_secret(value: str) -> str:
    if not value:
        return ""

    if len(value) <= 8:
        return "*" * len(value)

    return f"{value[:4]}{'*' * max(4, len(value) - 8)}{value[-4:]}"


async def _jwks():
    global _jwks_cache

    if _jwks_cache:
        return _jwks_cache

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{settings.keycloak_issuer}/protocol/openid-connect/certs")
        response.raise_for_status()
        _jwks_cache = response.json()

    return _jwks_cache


async def verify_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
        keys = await _jwks()

        key = next(key for key in keys["keys"] if key["kid"] == header["kid"])

        return jwt.decode(
            token,
            key,
            algorithms=[key["alg"]],
            audience=settings.keycloak_audience,
            options={"verify_aud": True},
        )

    except (JWTError, StopIteration, KeyError) as exc:
        raise ValueError(f"invalid token: {exc}") from exc


async def verify_token_admin(token: str) -> dict:
    user = await verify_token(token)

    roles = user.get("roles", [])

    if "admin" not in roles:
        raise PermissionError("admin only")

    return user


async def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    try:
        return await verify_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    try:
        user = await verify_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if "admin" not in user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user
