from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Grant
from app.schemas.schemas import GrantIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", status_code=201)
async def create(body: GrantIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    g = Grant(tenant_id=user.get("tenant_id","default"), **body.model_dump())
    s.add(g); await s.commit()
    return {"id": g.id}
@router.get("")
async def list_(s: AsyncSession = Depends(db)):
    res = await s.execute(select(Grant).order_by(Grant.deadline.asc()))
    return [{"id": g.id, "name": g.name, "funder": g.funder, "amount": g.amount, "currency": g.currency, "status": g.status, "deadline": g.deadline.isoformat() if g.deadline else None} for g in res.scalars().all()]
