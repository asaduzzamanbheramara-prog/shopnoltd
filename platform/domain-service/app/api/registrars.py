from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token_admin
from app.models.models import Registrar

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


@router.get("")
async def list_registrars(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Registrar))
    return [{"id": r.id, "name": r.name, "enabled": r.enabled} for r in res.scalars().all()]
