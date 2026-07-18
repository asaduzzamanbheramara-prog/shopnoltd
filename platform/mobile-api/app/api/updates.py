from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.get("/check")
async def check(code: str, version: str, build: int, user=Depends(current_user)):
    from sqlalchemy import desc, select

    from app.core.db import SessionLocal
    from app.models.models import AppRelease
    from app.schemas.schemas import ReleaseOut

    async with SessionLocal() as s:
        res = await s.execute(
            select(AppRelease)
            .where(AppRelease.code == code)
            .order_by(desc(AppRelease.created_at))
            .limit(1)
        )
        r = res.scalar_one_or_none()
        if not r:
            return {"update_available": False}
        if r.version != version or r.build > build:
            return {
                "update_available": True,
                "force": bool(r.force_update),
                "latest": ReleaseOut(
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
                ).model_dump(),
            }
    return {"update_available": False}
