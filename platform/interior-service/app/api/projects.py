from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Project
from app.schemas.schemas import ProjectIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("", status_code=201)
async def create(body: ProjectIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = Project(
        tenant_id=user.get("tenant_id", "default"), user_id=user["sub"], **body.model_dump()
    )
    s.add(p)
    await s.commit()
    await s.refresh(p)
    return {"id": p.id, "name": p.name}


@router.get("")
async def list_(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Project).where(Project.user_id == user["sub"]))
    return [
        {
            "id": p.id,
            "name": p.name,
            "style": p.style,
            "budget": p.budget,
            "created_at": p.created_at.isoformat(),
        }
        for p in res.scalars().all()
    ]


@router.get("/{proj_id}")
async def get(proj_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = (
        await s.execute(
            select(Project).where(Project.id == proj_id, Project.user_id == user["sub"])
        )
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "not found")
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "style": p.style,
        "budget": p.budget,
    }
