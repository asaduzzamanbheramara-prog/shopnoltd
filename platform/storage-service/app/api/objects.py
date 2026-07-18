import hashlib
import io
from datetime import timedelta

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.minio_client import client
from app.core.security import verify_token
from app.models.models import Object

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.put("/{bucket}/{key:path}")
async def upload(
    bucket: str,
    key: str,
    file: UploadFile = File(...),
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
):
    data = await file.read()
    size = len(data)
    sha = hashlib.sha256(data).hexdigest()
    client.put_object(bucket, key, io.BytesIO(data), size, content_type=file.content_type)
    o = Object(bucket_id=bucket, key=key, size=size, content_type=file.content_type)
    s.add(o)
    await s.commit()
    return {"bucket": bucket, "key": key, "size": size, "sha256": sha}


@router.get("/{bucket}/{key:path}/url")
async def presign(bucket: str, key: str, user=Depends(current_user)):
    url = client.presigned_get_object(bucket, key, expires=timedelta(hours=1))
    return {"url": url}


@router.delete("/{bucket}/{key:path}")
async def delete(bucket: str, key: str, user=Depends(current_user)):
    client.remove_object(bucket, key)
    return {"ok": True}
