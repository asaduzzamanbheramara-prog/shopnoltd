from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from datetime import datetime
from app.core.db import SessionLocal
from app.models.models import Transaction, TxStatus, Wallet
from app.providers.registry import get_provider
from app.models.models import PaymentMethod
router = APIRouter()
@router.post("/{provider}")
async def webhook(provider: str, request: Request):
    body = await request.body(); headers = dict(request.headers)
    try:
        method = PaymentMethod(provider)
    except ValueError:
        raise HTTPException(400, "unknown provider")
    p = get_provider(method)
    try:
        event = await p.verify_webhook(body, headers)
    except Exception as e:
        raise HTTPException(400, f"signature: {e}")
    async with SessionLocal() as s:
        external = event.get("external_id") or event.get("paymentID") or event.get("prepayId") or event.get("data", {}).get("prepayId")
        if not external:
            return {"received": True}
        res = await s.execute(select(Transaction).where(Transaction.external_id == str(external)))
        tx = res.scalar_one_or_none()
        if not tx: return {"received": True, "warning": "tx not found"}
        status = (event.get("status") or event.get("data", {}).get("status") or event.get("transactionStatus") or "").upper()
        if status in ("COMPLETED", "SUCCESS", "PAID", "CAPTURED", "TRADE_SUCCESS"):
            tx.status = TxStatus.completed; tx.completed_at = datetime.utcnow()
            wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id))
            w = wr.scalar_one()
            w.balance = Decimal(str(w.balance)) + Decimal(str(tx.amount)) - Decimal(str(tx.fee))
        elif status in ("FAILED", "EXPIRED", "CANCELED", "CANCELLED"):
            tx.status = TxStatus.failed; tx.completed_at = datetime.utcnow()
            if tx.type.value == "withdrawal":
                wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id))
                w = wr.scalar_one()
                w.frozen = Decimal(str(w.frozen)) - Decimal(str(tx.amount))
        await s.commit()
    return {"received": True}

