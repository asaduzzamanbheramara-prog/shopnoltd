from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Follow
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/{user_id}", status_code=201)
async def follow(user_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    if user_id == user["sub"]: raise HTTPException(400, "cannot follow yourself")
    existing = await s.execute(select(Follow).where(Follow.follower_id == user["sub"], Follow.followee_id == user_id))
    if existing.scalar_one_or_none(): return {"already": True}
    s.add(Follow(follower_id=user["sub"], followee_id=user_id, status="accepted"))
    await s.commit()
    return {"following": True}
@router.delete("/{user_id}")
async def unfollow(user_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Follow).where(Follow.follower_id == user["sub"], Follow.followee_id == user_id))
    f = res.scalar_one_or_none()
    if not f: raise HTTPException(404, "not following")
    await s.delete(f); await s.commit()
    return {"unfollowed": True}
@router.get("/following")
async def following(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Follow).where(Follow.follower_id == user["sub"]))
    return [r.followee_id for r in res.scalars().all()]
@router.get("/followers")
async def followers(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Follow).where(Follow.followee_id == user["sub"]))
    return [r.follower_id for r in res.scalars().all()]
