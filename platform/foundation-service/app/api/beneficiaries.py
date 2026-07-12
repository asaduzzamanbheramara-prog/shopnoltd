from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Beneficiary
from app.schemas.schemas import BeneficiaryIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", status_code=201)
async def create(body: BeneficiaryIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    b = Beneficiary(tenant_id=user.get("tenant_id","default"), **body.model_dump())
    s.add(b); await s.commit()
    return {"id": b.id}
@router.get("")
async def list_(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Beneficiary).where(Beneficiary.tenant_id == user.get("tenant_id","default")))
    return [{"id": b.id, "name": b.name, "type": b.type, "location": b.location, "aid_received": b.aid_received} for b in res.scalars().all()]
