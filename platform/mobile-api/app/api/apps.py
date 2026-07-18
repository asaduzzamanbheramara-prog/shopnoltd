from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token_admin
from app.models.models import AppRelease
from app.schemas.schemas import ReleaseIn, ReleaseOut

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


@router.get("", response_model=list[dict])
async def list_apps():
    """Public endpoint listing all Shopnoltd apps."""
    return [
        {
            "code": "shopno-survey",
            "name": "Shopnoltd Survey",
            "icon": "📋",
            "description": "Field data collection, forms, and case management.",
        },
        {
            "code": "shopno-chat",
            "name": "Shopnoltd Chat",
            "icon": "💬",
            "description": "Customer chat and support.",
        },
        {
            "code": "shopno-meet",
            "name": "Shopnoltd Meet",
            "icon": "📹",
            "description": "Video conferencing.",
        },
        {
            "code": "shopno-live",
            "name": "Shopnoltd Live",
            "icon": "🔴",
            "description": "Live streaming.",
        },
        {
            "code": "shopno-drive",
            "name": "Shopnoltd Drive",
            "icon": "☁️",
            "description": "Cloud storage and sync.",
        },
        {
            "code": "shopno-mail",
            "name": "Shopnoltd Mail",
            "icon": "✉️",
            "description": "Email client.",
        },
    ]


@router.get("/{code}/latest", response_model=ReleaseOut)
async def latest(code: str, s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(AppRelease)
        .where(AppRelease.code == code)
        .order_by(desc(AppRelease.created_at))
        .limit(1)
    )
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(404, "no release")
    return ReleaseOut(
        code=r.code,
        version=r.version,
        build=r.build,
        apk_url=r.apk_path,
        sha256=r.sha256,
        size_bytes=r.size_bytes,
        min_os_version=r.min_os_version,
        force_update=bool(r.force_update),
        release_notes=r.release_notes or "",
        published_at=r.created_at.isoformat(),
    )


@router.post("", status_code=201)
async def publish(body: ReleaseIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    r = AppRelease(**body.model_dump())
    s.add(r)
    await s.commit()
    return {"id": r.id, "version": r.version}
