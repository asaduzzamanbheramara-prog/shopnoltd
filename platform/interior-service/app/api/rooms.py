from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Room, Project
from app.schemas.schemas import RoomIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/{project_id}", status_code=201)
async def add(project_id: str, body: RoomIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = (await s.execute(select(Project).where(Project.id == project_id, Project.user_id == user["sub"]))).scalar_one_or_none()
    if not p: raise HTTPException(404, "project not found")
    r = Room(project_id=project_id, **body.model_dump())
    s.add(r); await s.commit()
    return {"id": r.id, "area_m2": r.width_m * r.length_m}
@router.get("/by-project/{project_id}")
async def list_rooms(project_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Room).where(Room.project_id == project_id))
    return [{"id": r.id, "name": r.name, "w": r.width_m, "l": r.length_m, "h": r.height_m, "color": r.color, "area_m2": r.width_m * r.length_m} for r in res.scalars().all()]
