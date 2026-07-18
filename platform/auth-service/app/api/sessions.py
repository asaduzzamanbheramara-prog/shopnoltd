from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Session

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.get("")
async def list_(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(Session).where(
            Session.user_id == user.get("email", user["sub"]), Session.active == True
        )
    )
    return [
        {
            "id": x.id,
            "device": x.device,
            "ip": x.ip,
            "user_agent": x.user_agent,
            "created_at": x.created_at.isoformat(),
            "last_seen": x.last_seen.isoformat(),
        }
        for x in res.scalars().all()
    ]


@router.delete("/{sess_id}")
async def revoke(sess_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    sess = (await s.execute(select(Session).where(Session.id == sess_id))).scalar_one_or_none()
    if not sess:
        from fastapi import HTTPException

        raise HTTPException(404, "not found")
    sess.active = False
    sess.revoked_at = datetime.utcnow()
    await s.commit()
    return {"ok": True}
