from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Wallet, Transaction, TxType, TxStatus
from app.schemas.schemas import TransferIn, TxOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uuid
router = APIRouter()
bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", response_model=TxOut, status_code=201)
async def internal_transfer(body: TransferIn, user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"], Wallet.currency == body.currency.upper()))
    src = res.scalar_one_or_none()
    if not src: raise HTTPException(404, "source wallet not found")
    if Decimal(str(src.balance)) < Decimal(str(body.amount)):
        raise HTTPException(400, "insufficient funds")
    res = await s.execute(select(Wallet).where(Wallet.user_id == body.to_user_id, Wallet.currency == body.currency.upper()))
    dst = res.scalar_one_or_none()
    if not dst:
        dst = Wallet(tenant_id=user.get("tenant_id", "default"), user_id=body.to_user_id, currency=body.currency.upper(), balance=0); s.add(dst); await s.flush()
    src.balance = Decimal(str(src.balance)) - Decimal(str(body.amount))
    dst.balance = Decimal(str(dst.balance)) + Decimal(str(body.amount))
    tx = Transaction(tenant_id=user.get("tenant_id", "default"), wallet_id=src.id, type=TxType.transfer, method="transfer", status=TxStatus.completed, amount=body.amount, currency=body.currency.upper(), fee=0, meta={"to": body.to_user_id, "note": body.note})
    s.add(tx); await s.commit()
    return TxOut(id=str(tx.id), type=tx.type, method=tx.method, status=tx.status, amount=float(tx.amount), fee=0, currency=tx.currency, reference=None, created_at=tx.created_at.isoformat(), completed_at=tx.created_at.isoformat())

