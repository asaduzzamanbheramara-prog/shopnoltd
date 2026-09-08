from fastapi import Header, HTTPException

from app.core.config import settings


def require_internal_key(x_internal_api_key: str = Header(...)):
    if not settings.internal_api_key:
        raise HTTPException(500, "INTERNAL_API_KEY is not configured; refusing privileged exchange operation")
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(403, "Invalid internal API key")
    return True
