from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Lesson
from app.schemas.schemas import LessonIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("", status_code=201)
async def add(body: LessonIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(func_count := Lesson).where(Lesson.course_id == body.course_id))
    cnt = len(res.scalars().all())
    l = Lesson(
        course_id=body.course_id,
        idx=cnt,
        title=body.title,
        content=body.content,
        video_url=body.video_url,
        duration_min=body.duration_min,
    )
    s.add(l)
    await s.commit()
    return {"id": l.id, "idx": l.idx}


@router.get("/by-course/{course_id}")
async def list_lessons(course_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.idx.asc())
    )
    return [
        {
            "id": l.id,
            "idx": l.idx,
            "title": l.title,
            "video_url": l.video_url,
            "duration_min": l.duration_min,
        }
        for l in res.scalars().all()
    ]
