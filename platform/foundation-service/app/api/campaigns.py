from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Campaign
from app.schemas.schemas import CampaignIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", status_code=201)
async def create(body: CampaignIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    c = Campaign(tenant_id=user.get("tenant_id","default"), **body.model_dump())
    s.add(c); await s.commit()
    return {"id": c.id, "name": c.name}
@router.get("")
async def list_(s: AsyncSession = Depends(db)):
    res = await s.execute(select(Campaign).where(Campaign.active == 1))
    return [{"id": c.id, "name": c.name, "goal": c.goal_amount, "raised": c.raised_amount, "progress_pct": (c.raised_amount / c.goal_amount * 100) if c.goal_amount else 0} for c in res.scalars().all()]
