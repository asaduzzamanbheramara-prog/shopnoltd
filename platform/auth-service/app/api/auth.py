import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token
from app.models.models import Session
from app.schemas.schemas import LoginIn, LoginOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/login", response_model=LoginOut)
async def login(body: LoginIn, request: Request, s: AsyncSession = Depends(db)):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "shopnoltd-web", "username": body.email, "password": body.password})
    if r.status_code != 200: raise HTTPException(401, "invalid credentials")
    d = r.json()
    sess = Session(user_id=body.email, ip=request.client.host if request.client else "", user_agent=request.headers.get("user-agent",""), device=body.device)
    s.add(sess); await s.commit()
    return LoginOut(access_token=d["access_token"], refresh_token=d["refresh_token"], expires_in=d.get("expires_in", 300), session_id=sess.id)
@router.post("/refresh")
async def refresh(refresh_token: str, s: AsyncSession = Depends(db)):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token",
            data={"grant_type": "refresh_token", "client_id": "shopnoltd-web", "refresh_token": refresh_token})
    r.raise_for_status(); return r.json()
@router.post("/logout")
async def logout(creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)):
    payload = await verify_token(creds.credentials)
    res = await s.execute(select(Session).where(Session.user_id == payload.get("email", payload["sub"]), Session.active == True))
    for sess in res.scalars().all():
        sess.active = False; sess.revoked_at = datetime.utcnow()
    await s.commit()
    return {"ok": True}
