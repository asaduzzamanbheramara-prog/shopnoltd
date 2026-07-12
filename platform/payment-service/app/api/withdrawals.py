from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Wallet, Transaction, TxType, TxStatus
from app.schemas.schemas import WithdrawalIn, TxOut
from app.providers.registry import get_provider
from app.core.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uuid
router = APIRouter()
bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", response_model=TxOut, status_code=201)
async def create_withdrawal(body: WithdrawalIn, user = Depends(current_user), s: AsyncSession = Depends(db)):
    if body.amount < settings.min_withdrawal or body.amount > settings.max_withdrawal:
        raise HTTPException(400, "amount out of range")
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"], Wallet.currency == body.currency.upper()))
    w = res.scalar_one_or_none()
    if not w: raise HTTPException(404, "wallet not found")
    if Decimal(str(w.balance)) < Decimal(str(body.amount)):
        raise HTTPException(400, "insufficient funds")
    w.frozen = Decimal(str(w.frozen)) + Decimal(str(body.amount))
    tx = Transaction(tenant_id=user.get("tenant_id", "default"), wallet_id=w.id, type=TxType.withdrawal, method=body.method, status=TxStatus.requires_approval if settings.admin_approval_required else TxStatus.processing, amount=body.amount, currency=body.currency.upper(), fee=body.amount * settings.platform_fee_pct / 100, meta=body.metadata)
    s.add(tx); await s.flush()
    provider = get_provider(body.method)
    out = await provider.create_withdrawal(tx, destination=body.destination)
    if out.get("status") == "requires_approval":
        tx.status = TxStatus.requires_approval
    else:
        tx.status = TxStatus.processing
    tx.external_id = out.get("external_id")
    await s.commit()
    return TxOut(id=str(tx.id), type=tx.type, method=tx.method, status=tx.status, amount=float(tx.amount), fee=float(tx.fee), currency=tx.currency, reference=tx.external_id, created_at=tx.created_at.isoformat(), completed_at=None, approval_url=out.get("approval_url"))

