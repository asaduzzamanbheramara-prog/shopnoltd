from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Post, PostView

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("/{post_id}")
async def record_view(post_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    post = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not post:
        raise HTTPException(404, "post not found")
    existing = await s.execute(select(PostView).where(PostView.post_id == post_id, PostView.user_id == user["sub"]))
    if existing.scalar_one_or_none():
        return {"viewed": True, "unique": False}
    s.add(PostView(post_id=post_id, user_id=user["sub"]))
    await s.commit()
    return {"viewed": True, "unique": True}


@router.get("/{post_id}/count")
async def view_count(post_id: str, s: AsyncSession = Depends(db)):
    from sqlalchemy import func
    count = await s.scalar(select(func.count(PostView.id)).where(PostView.post_id == post_id))
    return {"view_count": int(count or 0)}
