"""Private, per-user file storage endpoints backed by MinIO."""

import io
import re
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.minio_client import client
from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()
BUCKET = "shopno-user-files"
MAX_FILE_BYTES = 25 * 1024 * 1024


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc


def owner_prefix(user: dict) -> str:
    subject = str(user.get("sub") or "")
    if not subject or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", subject):
        raise HTTPException(403, "Account identifier is unavailable")
    return f"users/{subject}/"


def owned_key(user: dict, key: str) -> str:
    # Validate the raw path before pathlib normalization: PurePosixPath removes
    # repeated separators and "." segments, which can hide malformed input.
    if (
        not key
        or key.startswith("/")
        or "\\" in key
        or "\x00" in key
        or any(part in {"", ".", ".."} for part in key.split("/"))
    ):
        raise HTTPException(400, "Invalid file path")
    if len(key.encode("utf-8")) > 480:
        raise HTTPException(400, "File name is too long")
    return owner_prefix(user) + key


def ensure_bucket():
    if not client.bucket_exists(BUCKET):
        client.make_bucket(BUCKET)


@router.get("")
async def list_files(user=Depends(current_user)):
    ensure_bucket()
    prefix = owner_prefix(user)
    objects = client.list_objects(BUCKET, prefix=prefix, recursive=True)
    return [
        {
            "name": obj.object_name[len(prefix):],
            "size": obj.size,
            "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
            "etag": obj.etag,
        }
        for obj in objects
        if obj.object_name and obj.object_name.startswith(prefix)
    ]


@router.post("/{key:path}", status_code=201)
async def upload_file(key: str, file: UploadFile = File(...), user=Depends(current_user)):
    object_key = owned_key(user, key)
    data = await file.read(MAX_FILE_BYTES + 1)
    if not data:
        raise HTTPException(400, "Uploaded file is empty")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, "Maximum file size is 25 MB")
    ensure_bucket()
    content_type = file.content_type or "application/octet-stream"
    client.put_object(BUCKET, object_key, io.BytesIO(data), len(data), content_type=content_type)
    return {"name": key, "size": len(data), "content_type": content_type}


@router.get("/{key:path}")
async def download_file(key: str, user=Depends(current_user)):
    object_key = owned_key(user, key)
    try:
        obj = client.get_object(BUCKET, object_key)
        try:
            data = obj.read()
            content_type = obj.headers.get("Content-Type", "application/octet-stream")
        finally:
            obj.close()
            obj.release_conn()
    except Exception as exc:
        raise HTTPException(404, "File not found") from exc
    filename = PurePosixPath(key).name.replace('"', "")
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{key:path}")
async def delete_file(key: str, user=Depends(current_user)):
    object_key = owned_key(user, key)
    try:
        client.remove_object(BUCKET, object_key)
    except Exception as exc:
        raise HTTPException(404, "File not found") from exc
    return {"ok": True}
