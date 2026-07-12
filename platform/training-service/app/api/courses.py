from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Course
from app.schemas.schemas import CourseIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", status_code=201)
async def create(body: CourseIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    c = Course(tenant_id=user.get("tenant_id","default"), instructor_id=user["sub"], **body.model_dump())
    s.add(c); await s.commit()
    return {"id": c.id, "code": c.code}
@router.get("")
async def list_published(s: AsyncSession = Depends(db)):
    res = await s.execute(select(Course).where(Course.published == 1))
    return [{"id": c.id, "code": c.code, "title": c.title, "level": c.level, "price": c.price, "duration_hours": c.duration_hours} for c in res.scalars().all()]
@router.get("/{code}")
async def get_by_code(code: str, s: AsyncSession = Depends(db)):
    c = (await s.execute(select(Course).where(Course.code == code))).scalar_one_or_none()
    if not c: raise HTTPException(404, "course not found")
    return {"id": c.id, "code": c.code, "title": c.title, "description": c.description, "level": c.level, "price": c.price, "duration_hours": c.duration_hours}
@router.post("/{code}/publish")
async def publish(code: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    c = (await s.execute(select(Course).where(Course.code == code, Course.instructor_id == user["sub"]))).scalar_one_or_none()
    if not c: raise HTTPException(404, "not found or not your course")
    c.published = 1
    await s.commit()
    return {"published": True}
