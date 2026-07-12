from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Wallet, Transaction, TxType, TxStatus
from app.schemas.schemas import DepositIn, TxOut
from app.providers.registry import get_provider
from app.core.config import settings
from app.providers.exchange_client import convert_if_needed
import uuid
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter()
bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", response_model=TxOut, status_code=201)
async def create_deposit(body: DepositIn, user = Depends(current_user), s: AsyncSession = Depends(db)):
    if body.amount < settings.min_deposit or body.amount > settings.max_deposit:
        raise HTTPException(400, "amount out of range")
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"], Wallet.currency == body.currency.upper()))
    w = res.scalar_one_or_none()
    if not w: w = Wallet(tenant_id=user.get("tenant_id", "default"), user_id=user["sub"], currency=body.currency.upper(), balance=0); s.add(w); await s.flush()
    tx = Transaction(tenant_id=user.get("tenant_id", "default"), wallet_id=w.id, type=TxType.deposit, method=body.method, status=TxStatus.pending, amount=body.amount, fee=0, currency=body.currency.upper(), meta=body.metadata)
    s.add(tx); await s.flush()
    provider = get_provider(body.method)
    out = await provider.create_deposit(tx, return_url=body.return_url)
    tx.external_id = out.get("external_id")
    await s.commit()
    return TxOut(id=str(tx.id), type=tx.type, method=tx.method, status=tx.status, amount=float(tx.amount), fee=0, currency=tx.currency, reference=tx.external_id, created_at=tx.created_at.isoformat(), completed_at=None, redirect_url=out.get("redirect_url"), qr_code=out.get("qr_code"), address=out.get("address"), approval_url=out.get("approval_url"))
@router.get("/{tx_id}", response_model=TxOut)
async def get_deposit(tx_id: str, user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Transaction).where(Transaction.id == uuid.UUID(tx_id), Transaction.tenant_id == user.get("tenant_id", "default")))
    tx = res.scalar_one_or_none()
    if not tx: raise HTTPException(404, "tx not found")
    return TxOut(id=str(tx.id), type=tx.type, method=tx.method, status=tx.status, amount=float(tx.amount), fee=float(tx.fee), currency=tx.currency, reference=tx.external_id, created_at=tx.created_at.isoformat(), completed_at=tx.completed_at.isoformat() if tx.completed_at else None)

