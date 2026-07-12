from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Wallet
from app.schemas.schemas import WalletOut
from sqlalchemy import select
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter()
bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.get("", response_model=list[WalletOut])
async def list_wallets(user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"]))
    return res.scalars().all()
@router.get("/{currency}", response_model=WalletOut)
async def get_wallet(currency: str, user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"], Wallet.currency == currency.upper()))
    w = res.scalar_one_or_none()
    if not w: raise HTTPException(404, "wallet not found")
    return w

