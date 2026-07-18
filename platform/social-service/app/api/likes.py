from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Like, Post

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("/{post_id}", status_code=201)
async def like(post_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    existing = await s.execute(
        select(Like).where(Like.post_id == post_id, Like.user_id == user["sub"])
    )
    if existing.scalar_one_or_none():
        return {"already": True}
    s.add(Like(post_id=post_id, user_id=user["sub"]))
    p = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "post not found")
    p.like_count = (p.like_count or 0) + 1
    await s.commit()
    return {"liked": True, "like_count": p.like_count}


@router.delete("/{post_id}")
async def unlike(post_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Like).where(Like.post_id == post_id, Like.user_id == user["sub"]))
    l = res.scalar_one_or_none()
    if not l:
        raise HTTPException(404, "not liked")
    await s.delete(l)
    p = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one()
    p.like_count = max(0, (p.like_count or 1) - 1)
    await s.commit()
    return {"unliked": True, "like_count": p.like_count}


@router.get("/{post_id}")
async def likers(post_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Like).where(Like.post_id == post_id))
    return [
        {"user_id": l.user_id, "created_at": l.created_at.isoformat()} for l in res.scalars().all()
    ]
