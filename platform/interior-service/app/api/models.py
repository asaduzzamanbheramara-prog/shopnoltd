import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Model3D, Project

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("/{project_id}", status_code=201)
async def upload(
    project_id: str,
    name: str,
    fmt: str,
    file: UploadFile = File(...),
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
):
    p = (
        await s.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user["sub"])
        )
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "project not found")
    data = await file.read()
    key = f"interior/{project_id}/{name}.{fmt}"
    async with httpx.AsyncClient() as c:
        r = await c.put(
            f"http://storage-service.shopno-platform.svc.cluster.local:9000/api/v1/objects/shopno-3d/{key}",
            files={"file": (name + "." + fmt, data, file.content_type)},
        )
    m = Model3D(
        project_id=project_id,
        name=name,
        format=fmt,
        file_path=f"shopno-3d/{key}",
        size_bytes=len(data),
    )
    s.add(m)
    await s.commit()
    return {"id": m.id, "key": key, "size": len(data)}


@router.get("/by-project/{project_id}")
async def list_models(project_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Model3D).where(Model3D.project_id == project_id))
    return [
        {
            "id": m.id,
            "name": m.name,
            "format": m.format,
            "size": m.size_bytes,
            "url": f"http://storage-service.shopno-platform.svc.cluster.local:9000/api/v1/objects/{m.file_path}/url",
        }
        for m in res.scalars().all()
    ]
