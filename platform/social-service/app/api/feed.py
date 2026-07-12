from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, and_
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Post, Follow
from app.schemas.schemas import PostOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.get("/global", response_model=list[PostOut])
async def global_feed(s: AsyncSession = Depends(db), limit: int = Query(50, le=200), offset: int = 0):
    res = await s.execute(select(Post).where(Post.visibility == "public").order_by(desc(Post.published_at)).limit(limit).offset(offset))
    return [PostOut(id=p.id, user_id=p.user_id, content=p.content, media=p.media or [], visibility=p.visibility, published_at=p.published_at.isoformat(), like_count=p.like_count, share_count=p.share_count, comment_count=p.comment_count) for p in res.scalars().all()]
@router.get("/me", response_model=list[PostOut])
async def my_feed(user=Depends(current_user), s: AsyncSession = Depends(db), limit: int = Query(50, le=200), offset: int = 0):
    # posts from people I follow + my own
    f = await s.execute(select(Follow.followee_id).where(Follow.follower_id == user["sub"], Follow.status == "accepted"))
    followees = [r[0] for r in f.all()] + [user["sub"]]
    res = await s.execute(select(Post).where(Post.user_id.in_(followees), Post.visibility.in_(["public","tenant","friends"])).order_by(desc(Post.published_at)).limit(limit).offset(offset))
    return [PostOut(id=p.id, user_id=p.user_id, content=p.content, media=p.media or [], visibility=p.visibility, published_at=p.published_at.isoformat(), like_count=p.like_count, share_count=p.share_count, comment_count=p.comment_count) for p in res.scalars().all()]
