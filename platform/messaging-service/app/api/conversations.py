from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Conversation, Participant
from app.schemas.schemas import ConvIn, ConvOut

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("", response_model=ConvOut, status_code=201)
async def create(body: ConvIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    c = Conversation(tenant_id=user.get("tenant_id", "default"), type=body.type, title=body.title)
    s.add(c)
    await s.flush()
    s.add(Participant(conversation_id=c.id, user_id=user["sub"], role="owner"))
    for p in body.participants:
        if p != user["sub"]:
            s.add(Participant(conversation_id=c.id, user_id=p))
    await s.commit()
    await s.refresh(c)
    return ConvOut(id=c.id, type=c.type, title=c.title, created_at=c.created_at.isoformat())


@router.get("", response_model=list[ConvOut])
async def mine(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(Conversation)
        .join(Participant, Participant.conversation_id == Conversation.id)
        .where(Participant.user_id == user["sub"])
        .order_by(Conversation.created_at.desc())
    )
    return [
        ConvOut(id=c.id, type=c.type, title=c.title, created_at=c.created_at.isoformat())
        for c in res.scalars().all()
    ]


@router.get("/{conv_id}")
async def detail(conv_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(Participant).where(
            Participant.conversation_id == conv_id, Participant.user_id == user["sub"]
        )
    )
    if not res.scalar_one_or_none():
        raise HTTPException(403, "not a participant")
    return {"id": conv_id}
