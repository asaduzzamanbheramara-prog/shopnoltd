import hashlib
import io
from datetime import timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.minio_client import client
from app.core.security import verify_token
from app.models.models import Object

router = APIRouter()
bearer = HTTPBearer()
BLOG_BUCKET = "shopno-blog"
BLOG_MAX_BYTES = 8 * 1024 * 1024
BLOG_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


def blog_key_for_user(user: dict, key: str) -> str:
    prefix = f"blog/{user.get('sub')}/"
    if not key.startswith(prefix):
        raise HTTPException(403, "Blog object is not owned by this user")
    return key


@router.put("/{bucket}/{key:path}")
async def upload(
    bucket: str,
    key: str,
    file: UploadFile = File(...),
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
):
    if bucket == BLOG_BUCKET:
        key = blog_key_for_user(user, key)
        if file.content_type not in BLOG_TYPES:
            raise HTTPException(415, "Only JPEG, PNG, WebP and GIF images are allowed for blog covers")
    data = await file.read()
    size = len(data)
    if bucket == BLOG_BUCKET and size > BLOG_MAX_BYTES:
        raise HTTPException(413, "Blog cover image must be 8 MB or smaller")
    if not data:
        raise HTTPException(400, "Uploaded file is empty")
    sha = hashlib.sha256(data).hexdigest()
    if not client.bucket_exists(bucket):
        if bucket != BLOG_BUCKET:
            raise HTTPException(404, "Storage bucket not found")
        client.make_bucket(bucket)
    client.put_object(bucket, key, io.BytesIO(data), size, content_type=file.content_type)
    o = Object(bucket_id=bucket, key=key, size=size, content_type=file.content_type)
    s.add(o)
    await s.commit()
    public_url = f"/api/v1/objects/public/{bucket}/{key}"
    return {"bucket": bucket, "key": key, "size": size, "sha256": sha, "url": public_url}


@router.get("/public/{bucket}/{key:path}")
async def public_object(bucket: str, key: str):
    if bucket != BLOG_BUCKET or not key.startswith("blog/"):
        raise HTTPException(404, "Public object not found")
    try:
        obj = client.get_object(bucket, key)
        try:
            data = obj.read()
            content_type = obj.headers.get("Content-Type", "application/octet-stream")
        finally:
            obj.close()
            obj.release_conn()
    except Exception as exc:
        raise HTTPException(404, "Public object not found") from exc
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})


@router.get("/{bucket}/{key:path}/url")
async def presign(bucket: str, key: str, user=Depends(current_user)):
    url = client.presigned_get_object(bucket, key, expires=timedelta(hours=1))
    return {"url": url}


@router.delete("/{bucket}/{key:path}")
async def delete(bucket: str, key: str, user=Depends(current_user)):
    if bucket == BLOG_BUCKET:
        key = blog_key_for_user(user, key)
    client.remove_object(bucket, key)
    return {"ok": True}
