import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Stream
from app.schemas.schemas import StreamIn, StreamOut

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("", response_model=StreamOut, status_code=201)
async def create(body: StreamIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    sk = secrets.token_urlsafe(24)
    st = Stream(
        tenant_id=user.get("tenant_id", "default"),
        owner_id=user["sub"],
        name=body.name,
        title=body.title,
        description=body.description,
        recording_enabled=body.recording_enabled,
    )
    s.add(st)
    await s.commit()
    await s.refresh(st)
    return StreamOut(
        id=st.id,
        name=st.name,
        title=st.title,
        description=st.description,
        is_live=False,
        viewer_count=0,
        rtmp_url="rtmp://live.shopnoltd.dpdns.org/live",
        stream_key=sk,
        watch_url=f"https://live.shopnoltd.dpdns.org/{st.name}",
        recording_storage_path=f"s3://shopnoltd-live/{st.name}/",
    )


@router.get("", response_model=list[StreamOut])
async def list_streams(s: AsyncSession = Depends(db)):
    res = await s.execute(select(Stream).order_by(Stream.created_at.desc()).limit(100))
    out = []
    for st in res.scalars().all():
        out.append(
            StreamOut(
                id=st.id,
                name=st.name,
                title=st.title,
                description=st.description,
                is_live=st.is_live,
                viewer_count=st.viewer_count,
                rtmp_url="rtmp://live.shopnoltd.dpdns.org/live",
                stream_key="***",
                watch_url=f"https://live.shopnoltd.dpdns.org/{st.name}",
                recording_storage_path=f"s3://shopnoltd-live/{st.name}/",
            )
        )
    return out


@router.get("/{name}", response_model=StreamOut)
async def get_stream(name: str, s: AsyncSession = Depends(db)):
    st = (await s.execute(select(Stream).where(Stream.name == name))).scalar_one_or_none()
    if not st:
        raise HTTPException(404, "stream not found")
    return StreamOut(
        id=st.id,
        name=st.name,
        title=st.title,
        description=st.description,
        is_live=st.is_live,
        viewer_count=st.viewer_count,
        rtmp_url="rtmp://live.shopnoltd.dpdns.org/live",
        stream_key="***",
        watch_url=f"https://live.shopnoltd.dpdns.org/{st.name}",
        recording_storage_path=f"s3://shopnoltd-live/{st.name}/",
    )


@router.post("/{name}/status")
async def set_status(
    name: str, is_live: bool, viewer_count: int = 0, s: AsyncSession = Depends(db)
):
    """Webhook from Owncast: updates DB and can notify followers."""
    st = (await s.execute(select(Stream).where(Stream.name == name))).scalar_one_or_none()
    if not st:
        raise HTTPException(404, "stream not found")
    st.is_live = is_live
    st.viewer_count = viewer_count
    if is_live:
        async with httpx.AsyncClient() as c:
            await c.post(
                "http://notification-service.shopno-platform.svc.cluster.local:8080/api/v1/notifications/broadcast",
                json={
                    "channel": "push",
                    "title": f"🔴 {st.title} is live",
                    "body": st.description or st.name,
                    "meta": {"stream": st.name},
                },
            )
    await s.commit()
    return {"ok": True}
