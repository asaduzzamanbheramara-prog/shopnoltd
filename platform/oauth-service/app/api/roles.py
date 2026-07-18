import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import verify_token_admin

router = APIRouter()
bearer = HTTPBearer()


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


ADMIN_URL = f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}"


async def kc_token():
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": settings.keycloak_admin_user,
                "password": settings.keycloak_admin_password,
            },
        )
    r.raise_for_status()
    return r.json()["access_token"]


@router.get("")
async def list_(user=Depends(admin)):
    tok = await kc_token()
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{ADMIN_URL}/roles", headers={"Authorization": f"Bearer {tok}"})
    r.raise_for_status()
    return r.json()


@router.post("")
async def create(name: str, description: str = "", user=Depends(admin)):
    tok = await kc_token()
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{ADMIN_URL}/roles",
            headers={"Authorization": f"Bearer {tok}"},
            json={"name": name, "description": description},
        )
    if r.status_code == 409:
        raise HTTPException(409, "role exists")
    r.raise_for_status()
    return {"name": name}
