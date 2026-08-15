from datetime import datetime
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Session
from app.schemas.schemas import LoginIn, LoginOut, SignupIn, SignupOut, SocialTokenIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


def _user_id(payload: dict) -> str:
    value = payload.get("email") or payload.get("preferred_username") or payload.get("sub")
    if not value:
        raise HTTPException(401, "token has no usable user identity")
    return value


async def _keycloak_token(data: dict):
    async with httpx.AsyncClient(timeout=15) as c:
        return await c.post(
            f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token",
            data=data,
        )


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("/signup", response_model=SignupOut, status_code=201)
async def signup(body: SignupIn):
    if len(body.password) < 8:
        raise HTTPException(422, "password must be at least 8 characters")
    if not settings.keycloak_admin_client_id or not settings.keycloak_admin_client_secret:
        raise HTTPException(503, "signup is not configured")

    token = await _keycloak_token(
        {
            "grant_type": "client_credentials",
            "client_id": settings.keycloak_admin_client_id,
            "client_secret": settings.keycloak_admin_client_secret,
        }
    )
    if token.status_code != 200:
        raise HTTPException(503, "identity administration is unavailable")

    admin_token = token.json()["access_token"]
    user = {
        "username": body.email,
        "email": body.email,
        "enabled": True,
        "emailVerified": False,
        "firstName": body.first_name,
        "lastName": body.last_name,
        "credentials": [
            {
                "type": "password",
                "value": body.password,
                "temporary": False,
            }
        ],
    }

    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=user,
        )
        if r.status_code == 409:
            raise HTTPException(409, "email already registered")
        if r.status_code != 201:
            raise HTTPException(502, "identity provider rejected signup")

        location = r.headers.get("location", "")
        user_id = location.rstrip("/").split("/")[-1] or None

        if settings.signup_verify_email and user_id:
            verify = await c.put(
                f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users/{user_id}/send-verify-email",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            if verify.status_code not in (204, 200):
                raise HTTPException(
                    502,
                    "account created but verification email could not be sent",
                )

    return SignupOut(
        ok=True,
        user_id=user_id,
        message="account created; verify your email",
    )


@router.get("/social/{provider}")
async def social_login(
    provider: str,
    redirect_uri: str,
    state: str | None = None,
    code_challenge: str | None = None,
):
    provider = provider.lower()
    if provider not in {"google", "facebook", "github"}:
        raise HTTPException(404, "unsupported social provider")

    params = {
        "client_id": settings.keycloak_web_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid profile email",
        "kc_idp_hint": provider,
    }
    if state:
        params["state"] = state
    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

    return {
        "provider": provider,
        "authorization_url": (
            f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
            f"/protocol/openid-connect/auth?{urlencode(params)}"
        ),
    }


@router.post("/social/token", response_model=LoginOut)
async def social_token(
    body: SocialTokenIn,
    request: Request,
    s: AsyncSession = Depends(db),
):
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.keycloak_web_client_id,
        "code": body.code,
        "redirect_uri": body.redirect_uri,
    }
    if body.code_verifier:
        data["code_verifier"] = body.code_verifier

    r = await _keycloak_token(data)
    if r.status_code != 200:
        raise HTTPException(401, "social login authorization code is invalid")

    d = r.json()
    async with httpx.AsyncClient(timeout=15) as c:
        info = await c.get(
            f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/userinfo",
            headers={"Authorization": f"Bearer {d['access_token']}"},
        )

    if info.status_code != 200:
        raise HTTPException(401, "could not resolve social account")

    user_id = _user_id(info.json())
    sess = Session(
        user_id=user_id,
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        device=body.device,
    )
    s.add(sess)
    await s.commit()

    return LoginOut(
        access_token=d["access_token"],
        refresh_token=d["refresh_token"],
        expires_in=d.get("expires_in", 300),
        session_id=sess.id,
    )


@router.post("/login", response_model=LoginOut)
async def login(body: LoginIn, request: Request, s: AsyncSession = Depends(db)):
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": settings.keycloak_web_client_id,
                "username": body.email,
                "password": body.password,
            },
        )
    if r.status_code != 200:
        raise HTTPException(401, "invalid credentials")
    d = r.json()
    sess = Session(
        user_id=body.email,
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        device=body.device,
    )
    s.add(sess)
    await s.commit()
    return LoginOut(
        access_token=d["access_token"],
        refresh_token=d["refresh_token"],
        expires_in=d.get("expires_in", 300),
        session_id=sess.id,
    )


@router.post("/refresh")
async def refresh(refresh_token: str, s: AsyncSession = Depends(db)):
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.keycloak_web_client_id,
                "refresh_token": refresh_token,
            },
        )
    r.raise_for_status()
    return r.json()


@router.post("/logout")
async def logout(
    creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)
):
    payload = await verify_token(creds.credentials)
    res = await s.execute(
        select(Session).where(Session.user_id == _user_id(payload), Session.active.is_(True))
    )
    for sess in res.scalars().all():
        sess.active = False
        sess.revoked_at = datetime.utcnow()
    await s.commit()
    return {"ok": True}
