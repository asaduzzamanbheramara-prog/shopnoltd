from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Post, Reaction

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.put("/{post_id}")
async def react(post_id: str, reaction: str = Query(..., min_length=1, max_length=32),
                user=Depends(current_user), s: AsyncSession = Depends(db)):
    post = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not post:
        raise HTTPException(404, "post not found")
    existing = (await s.execute(select(Reaction).where(
        Reaction.post_id == post_id, Reaction.user_id == user["sub"], Reaction.reaction == reaction
    ))).scalar_one_or_none()
    if not existing:
        s.add(Reaction(post_id=post_id, user_id=user["sub"], reaction=reaction))
        await s.commit()
    return {"reacted": True, "reaction": reaction}


@router.delete("/{post_id}")
async def unreact(post_id: str, reaction: str = Query(..., min_length=1, max_length=32),
                  user=Depends(current_user), s: AsyncSession = Depends(db)):
    row = (await s.execute(select(Reaction).where(
        Reaction.post_id == post_id, Reaction.user_id == user["sub"], Reaction.reaction == reaction
    ))).scalar_one_or_none()
    if row:
        await s.delete(row)
        await s.commit()
    return {"reacted": False, "reaction": reaction}


@router.get("/{post_id}")
async def reactions(post_id: str, s: AsyncSession = Depends(db)):
    rows = (await s.execute(select(Reaction).where(Reaction.post_id == post_id))).scalars().all()
    return [{"user_id": r.user_id, "reaction": r.reaction, "created_at": r.created_at.isoformat()} for r in rows]
