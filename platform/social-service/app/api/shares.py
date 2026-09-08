from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Post, Share
from app.schemas.schemas import ShareIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("/{post_id}", status_code=201)
async def share(post_id: str, body: ShareIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    post = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not post:
        raise HTTPException(404, "post not found")
    if body.target in {"twitter", "facebook", "linkedin"}:
        raise HTTPException(501, f"{body.target} sharing requires an enabled provider integration")
    s.add(Share(post_id=post_id, user_id=user["sub"], target=body.target))
    post.share_count = (post.share_count or 0) + 1
    await s.commit()
    return {"shared": True, "share_count": post.share_count, "target": body.target, "share_url": f"/post/{post_id}"}


@router.get("/{post_id}")
async def sharers(post_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Share).where(Share.post_id == post_id))
    return [{"user_id": sh.user_id, "target": sh.target, "created_at": sh.created_at.isoformat()} for sh in res.scalars().all()]
