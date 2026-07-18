from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Course, Enrollment

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("/{course_id}", status_code=201)
async def enroll(course_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    c = (await s.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "course not found")
    if (
        await s.execute(
            select(Enrollment).where(
                Enrollment.course_id == course_id, Enrollment.user_id == user["sub"]
            )
        )
    ).scalar_one_or_none():
        return {"already": True}
    e = Enrollment(course_id=course_id, user_id=user["sub"])
    s.add(e)
    await s.commit()
    return {"id": e.id, "status": "active"}


@router.post("/{enrollment_id}/progress")
async def update_progress(
    enrollment_id: str,
    progress_pct: float,
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
):
    e = (
        await s.execute(
            select(Enrollment).where(
                Enrollment.id == enrollment_id, Enrollment.user_id == user["sub"]
            )
        )
    ).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "not found")
    e.progress_pct = min(100.0, max(0.0, progress_pct))
    if e.progress_pct >= 100.0:
        e.status = "completed"
        e.completed_at = datetime.utcnow()
    await s.commit()
    return {"progress_pct": e.progress_pct, "status": e.status}


@router.get("/me")
async def my(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Enrollment).where(Enrollment.user_id == user["sub"]))
    return [
        {
            "id": e.id,
            "course_id": e.course_id,
            "status": e.status,
            "progress_pct": e.progress_pct,
            "enrolled_at": e.enrolled_at.isoformat(),
        }
        for e in res.scalars().all()
    ]
