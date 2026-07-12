from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Transaction
from app.schemas.schemas import TxOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter()
bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.get("", response_model=list[TxOut])
async def history(user = Depends(current_user), s: AsyncSession = Depends(db), limit: int = Query(50, le=200), offset: int = 0):
    res = await s.execute(select(Transaction).where(Transaction.tenant_id == user.get("tenant_id", "default")).order_by(Transaction.created_at.desc()).limit(limit).offset(offset))
    rows = res.scalars().all()
    return [TxOut(id=str(t.id), type=t.type, method=t.method, status=t.status, amount=float(t.amount), fee=float(t.fee), currency=t.currency, reference=t.external_id, created_at=t.created_at.isoformat(), completed_at=t.completed_at.isoformat() if t.completed_at else None) for t in rows]

