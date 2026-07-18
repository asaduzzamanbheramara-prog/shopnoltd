from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Donor
from app.schemas.schemas import DonorIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("", status_code=201)
async def create(body: DonorIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    d = Donor(
        tenant_id=user.get("tenant_id", "default"),
        name=body.name,
        email=body.email,
        phone=body.phone,
        is_anonymous=1 if body.is_anonymous else 0,
    )
    s.add(d)
    await s.commit()
    await s.refresh(d)
    return {"id": d.id, "name": d.name}


@router.get("")
async def list_(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Donor).where(Donor.tenant_id == user.get("tenant_id", "default")))
    return [
        {"id": d.id, "name": d.name, "email": d.email, "total_donated": d.total_donated}
        for d in res.scalars().all()
    ]
