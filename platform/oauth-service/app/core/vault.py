import os

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Fernet:
    key = os.getenv("PROFILE_SECRET_ENCRYPTION_KEY", "").strip()
    if not key:
        raise RuntimeError("PROFILE_SECRET_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise RuntimeError("PROFILE_SECRET_ENCRYPTION_KEY is invalid") from exc


def encrypt_secret(value: str) -> bytes:
    if not value:
        raise ValueError("secret value cannot be empty")
    return _fernet().encrypt(value.encode("utf-8"))


def decrypt_secret(value: bytes) -> str:
    try:
        return _fernet().decrypt(value).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("secret could not be decrypted") from exc
