import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token, verify_token_admin
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


def _user_name(payload: dict) -> str:
    name = (payload.get("name") or "").strip()
    if name:
        return name
    given = (payload.get("given_name") or "").strip()
    family = (payload.get("family_name") or "").strip()
    return " ".join(part for part in (given, family) if part)


def _user_out(u: UserMirror) -> UserOut:
    return UserOut(
        id=u.id,
        sub=u.keycloak_id,
        email=u.email,
        name=u.name or "",
        tenant_id=u.tenant_id,
        roles=u.roles or [],
    )


async def ensure_user_mirror(payload: dict, s: AsyncSession) -> UserMirror:
    keycloak_id = payload.get("sub")
    email = (payload.get("email") or "").strip()

    if not keycloak_id:
        raise HTTPException(401, "authenticated token is missing subject")
    if not email:
        raise HTTPException(400, "authenticated token is missing email")

    existing = (
        await s.execute(
            select(UserMirror).where(UserMirror.keycloak_id == keycloak_id)
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    email_owner = (
        await s.execute(select(UserMirror).where(UserMirror.email == email))
    ).scalar_one_or_none()
    if email_owner and email_owner.keycloak_id != keycloak_id:
        raise HTTPException(409, "email is already linked to another account")

    u = UserMirror(
        keycloak_id=keycloak_id,
        email=email,
        name=_user_name(payload),
        tenant_id=payload.get("tenant_id"),
        roles=payload.get("roles") or [],
        active=True,
    )
    s.add(u)

    try:
        await s.flush()
    except IntegrityError:
        await s.rollback()
        existing = (
            await s.execute(
                select(UserMirror).where(UserMirror.keycloak_id == keycloak_id)
            )
        ).scalar_one_or_none()
        if existing:
            return existing

        email_owner = (
            await s.execute(select(UserMirror).where(UserMirror.email == email))
        ).scalar_one_or_none()
        if email_owner and email_owner.keycloak_id != keycloak_id:
            raise HTTPException(409, "email is already linked to another account")
        raise HTTPException(409, "unable to provision account safely")

    await s.commit()
    await s.refresh(u)
    return u


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
    async with httpx.AsyncClient() as c:
        r2 = await c.get(
            f"{ADMIN_URL}/users?email={body.email}", headers={"Authorization": f"Bearer {tok}"}
        )
    kc_id = r2.json()[0]["id"]
    u = UserMirror(keycloak_id=kc_id, email=body.email, name=body.name, tenant_id=body.tenant_id)
    s.add(u)
    await s.commit()
    await s.refresh(u)
    return _user_out(u)


@router.get("", response_model=list[UserOut])
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(UserMirror).limit(500))
    return [_user_out(u) for u in res.scalars().all()]


@router.get("/me")
async def me(creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)):
    payload = await verify_token(creds.credentials)
    u = await ensure_user_mirror(payload, s)
    return _user_out(u)
