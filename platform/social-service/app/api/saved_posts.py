"""Authenticated saved-post collection and bookmark state."""
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Post, SavedPost

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as session:
        yield session


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


def media_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (TypeError, ValueError):
            return []
    return []


def post_out(post: Post) -> dict:
    return {
        "id": post.id,
        "user_id": post.user_id,
        "content": post.content,
        "media": media_list(post.media),
        "visibility": post.visibility,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "like_count": post.like_count or 0,
        "share_count": post.share_count or 0,
        "comment_count": post.comment_count or 0,
    }


@router.get("")
async def saved_posts(user=Depends(current_user), s: AsyncSession = Depends(db)):
    result = await s.execute(
        select(SavedPost, Post)
        .join(Post, Post.id == SavedPost.post_id)
        .where(SavedPost.user_id == user["sub"])
        .order_by(desc(SavedPost.created_at))
    )
    return [
        {**post_out(post), "saved_at": saved.created_at.isoformat() if saved.created_at else None}
        for saved, post in result.all()
    ]


@router.get("/{post_id}")
async def saved_state(post_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    post = (await s.execute(select(Post.id).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(404, "post not found")
    saved = await s.execute(
        select(SavedPost.id).where(SavedPost.post_id == post_id, SavedPost.user_id == user["sub"])
    )
    return {"saved": saved.scalar_one_or_none() is not None}


@router.put("/{post_id}")
async def save_post(post_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    post = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(404, "post not found")
    existing = await s.execute(
        select(SavedPost.id).where(SavedPost.post_id == post_id, SavedPost.user_id == user["sub"])
    )
    if existing.scalar_one_or_none() is not None:
        return {"saved": True}
    s.add(SavedPost(post_id=post_id, user_id=user["sub"]))
    try:
        await s.commit()
    except IntegrityError:
        await s.rollback()
        existing = await s.execute(
            select(SavedPost.id).where(SavedPost.post_id == post_id, SavedPost.user_id == user["sub"])
        )
        if existing.scalar_one_or_none() is None:
            raise
    return {"saved": True}


@router.delete("/{post_id}")
async def unsave_post(post_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    result = await s.execute(
        select(SavedPost).where(SavedPost.post_id == post_id, SavedPost.user_id == user["sub"])
    )
    saved = result.scalar_one_or_none()
    if saved is not None:
        await s.delete(saved)
        await s.commit()
    return {"saved": False}
