import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Campaign, Donation, Donor
from app.schemas.schemas import DonationIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("", status_code=201)
async def donate(body: DonationIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    donor = (await s.execute(select(Donor).where(Donor.id == body.donor_id))).scalar_one_or_none()
    if not donor:
        raise HTTPException(404, "donor not found")
    receipt = f"DON-{secrets.token_hex(6).upper()}"
    d = Donation(
        tenant_id=user.get("tenant_id", "default"),
        donor_id=body.donor_id,
        campaign_id=body.campaign_id,
        amount=body.amount,
        currency=body.currency,
        method=body.method,
        status="pending",
        receipt_no=receipt,
    )
    s.add(d)
    await s.commit()
    if body.campaign_id:
        c = (
            await s.execute(select(Campaign).where(Campaign.id == body.campaign_id))
        ).scalar_one_or_none()
        if c:
            c.raised_amount = (c.raised_amount or 0) + body.amount
    return {"id": d.id, "receipt_no": receipt, "status": "pending"}


@router.get("")
async def list_(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(Donation)
        .where(Donation.tenant_id == user.get("tenant_id", "default"))
        .order_by(Donation.created_at.desc())
        .limit(200)
    )
    return [
        {
            "id": d.id,
            "donor_id": d.donor_id,
            "amount": d.amount,
            "currency": d.currency,
            "method": d.method,
            "status": d.status,
            "receipt_no": d.receipt_no,
            "created_at": d.created_at.isoformat(),
        }
        for d in res.scalars().all()
    ]
