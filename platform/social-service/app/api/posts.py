from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Comment, Post
from app.schemas.schemas import CommentIn, PostIn, PostOut

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


def post_out(p: Post) -> PostOut:
    return PostOut(id=p.id, user_id=p.user_id, content=p.content, media=p.media or [],
                   visibility=p.visibility, published_at=p.published_at.isoformat(),
                   like_count=p.like_count or 0, share_count=p.share_count or 0,
                   comment_count=p.comment_count or 0)


@router.post("", response_model=PostOut, status_code=201)
async def create_post(body: PostIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = Post(tenant_id=user.get("tenant_id", "default"), user_id=user["sub"],
             content=body.content.strip(), media=body.media, visibility=body.visibility)
    if body.scheduled_at:
        p.scheduled_at = datetime.fromisoformat(body.scheduled_at)
        p.published_at = p.scheduled_at
    s.add(p)
    await s.commit()
    await s.refresh(p)
    return post_out(p)


@router.get("/{post_id}", response_model=PostOut)
async def get_post(post_id: str, s: AsyncSession = Depends(db)):
    p = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "post not found")
    return post_out(p)


@router.patch("/{post_id}", response_model=PostOut)
async def edit_post(post_id: str, body: PostIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "post not found")
    if p.user_id != user["sub"]:
        raise HTTPException(403, "not your post")
    p.content, p.media, p.visibility = body.content.strip(), body.media, body.visibility
    if body.scheduled_at:
        p.scheduled_at = datetime.fromisoformat(body.scheduled_at)
        p.published_at = p.scheduled_at
    p.updated_at = datetime.utcnow()
    await s.commit()
    await s.refresh(p)
    return post_out(p)


@router.delete("/{post_id}")
async def delete_post(post_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "post not found")
    if p.user_id != user["sub"]:
        raise HTTPException(403, "not your post")
    await s.delete(p)
    await s.commit()
    return {"ok": True}


@router.get("/by/{user_id}", response_model=list[PostOut])
async def posts_by_user(user_id: str, s: AsyncSession = Depends(db),
                        limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    res = await s.execute(select(Post).where(
        Post.user_id == user_id, Post.visibility.in_(["public", "tenant"])
    ).order_by(desc(Post.published_at)).limit(limit).offset(offset))
    return [post_out(p) for p in res.scalars().all()]


@router.post("/{post_id}/comments", status_code=201)
async def add_comment(post_id: str, body: CommentIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "post not found")
    if body.parent_id:
        parent = (await s.execute(select(Comment).where(
            Comment.id == body.parent_id, Comment.post_id == post_id
        ))).scalar_one_or_none()
        if not parent:
            raise HTTPException(400, "parent comment not found")
    c = Comment(post_id=post_id, user_id=user["sub"], body=body.body.strip(), parent_id=body.parent_id)
    s.add(c)
    p.comment_count = (p.comment_count or 0) + 1
    await s.commit()
    await s.refresh(c)
    return {"id": c.id, "post_id": post_id, "user_id": c.user_id, "parent_id": c.parent_id,
            "body": c.body, "created_at": c.created_at.isoformat()}


@router.get("/{post_id}/comments")
async def list_comments(post_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at.asc()))
    return [{"id": c.id, "user_id": c.user_id, "parent_id": c.parent_id, "body": c.body,
             "created_at": c.created_at.isoformat()} for c in res.scalars().all()]
