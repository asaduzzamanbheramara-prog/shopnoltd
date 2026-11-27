"""Authenticated read-only integration directory."""
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.integration_catalog import list_integrations
from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.get("/integrations/catalog")
async def integration_catalog(
    category: str | None = Query(default=None, max_length=80),
    q: str | None = Query(default=None, max_length=120),
    _user=Depends(current_user),
):
    """Browse known providers without claiming a connection or executing actions."""
    return list_integrations(category=category, query=q)
