from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Transaction
from app.schemas.schemas import TxOut
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        user = await verify_token(creds.credentials)
    except ValueError as exc:
        raise HTTPException(401, "invalid or expired authentication token") from exc
    if not user.get("sub"):
        raise HTTPException(401, "authentication subject missing")
    return user


@router.get("", response_model=list[TxOut])
async def history(
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    res = await s.execute(
        select(Transaction)
        .where(
            Transaction.tenant_id == user.get("tenant_id", "default"),
            Transaction.user_id == user["sub"],
        )
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = res.scalars().all()
    return [
        TxOut(
            id=str(t.id), type=t.type, method=t.method, status=t.status,
            amount=float(t.amount), fee=float(t.fee), currency=t.currency,
            reference=t.external_id, created_at=t.created_at.isoformat(),
            completed_at=t.completed_at.isoformat() if t.completed_at else None,
        )
        for t in rows
    ]
