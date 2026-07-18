import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token_admin
from app.models.models import UserMirror
from app.schemas.schemas import UserIn, UserOut

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


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


@router.post("", response_model=UserOut, status_code=201)
async def create(body: UserIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    tok = await kc_token()
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{ADMIN_URL}/users",
            headers={"Authorization": f"Bearer {tok}"},
            json={
                "email": body.email,
                "username": body.email,
                "firstName": body.name,
                "enabled": True,
                "emailVerified": False,
                "credentials": [{"type": "password", "value": body.password, "temporary": False}]
                if body.password
                else [],
            },
        )
    if r.status_code == 409:
        raise HTTPException(409, "user already exists")
    r.raise_for_status()
    # Find keycloak id
    async with httpx.AsyncClient() as c:
        r2 = await c.get(
            f"{ADMIN_URL}/users?email={body.email}", headers={"Authorization": f"Bearer {tok}"}
        )
    kc_id = r2.json()[0]["id"]
    u = UserMirror(keycloak_id=kc_id, email=body.email, name=body.name, tenant_id=body.tenant_id)
    s.add(u)
    await s.commit()
    await s.refresh(u)
    return UserOut(id=u.id, email=u.email, name=u.name, tenant_id=u.tenant_id, roles=u.roles or [])


@router.get("", response_model=list[UserOut])
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(UserMirror).limit(500))
    return [
        UserOut(id=u.id, email=u.email, name=u.name, tenant_id=u.tenant_id, roles=u.roles or [])
        for u in res.scalars().all()
    ]


@router.get("/me")
async def me(creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)):
    from app.core.security import verify_token

    payload = await verify_token(creds.credentials)
    u = (
        await s.execute(select(UserMirror).where(UserMirror.keycloak_id == payload["sub"]))
    ).scalar_one_or_none()
    if not u:
        return {
            "id": payload["sub"],
            "email": payload.get("email"),
            "tenant_id": payload.get("tenant_id"),
            "roles": payload.get("roles", []),
        }
    return UserOut(id=u.id, email=u.email, name=u.name, tenant_id=u.tenant_id, roles=u.roles or [])
