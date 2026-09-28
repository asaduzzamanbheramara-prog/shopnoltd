import io
import re
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from minio.commonconfig import CopySource
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.minio_client import client
from app.core.security import verify_token
from app.models.models import ProfileVideo, ProfileVideoUpload

router = APIRouter()
bearer = HTTPBearer()
BUCKET = "shopno-profile-videos"
PROFILES = {"data-management", "interior-business"}
CHUNK_SIZE = 8 * 1024 * 1024
MAX_BYTES = 500 * 1024 * 1024
MAX_PARTS = (MAX_BYTES + CHUNK_SIZE - 1) // CHUNK_SIZE
UPLOAD_TTL = timedelta(hours=24)
VIDEO_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm"}
RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


def _profile(slug: str) -> str:
    if slug not in PROFILES:
        raise HTTPException(404, "Profile not found")
    return slug


def _admin_roles(user: dict) -> bool:
    roles = set(user.get("roles", []))
    realm = set(user.get("realm_access", {}).get("roles", []))
    return bool(roles.intersection({"admin", "platform_admin"}) or realm.intersection({"admin", "platform_admin"}))


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        user = await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc
    if not _admin_roles(user):
        raise HTTPException(403, "Admin role required")
    return user


async def db():
    async with SessionLocal() as s:
        yield s


def _check_magic(content_type: str, data: bytes) -> bool:
    if content_type == "video/mp4":
        return len(data) >= 8 and data[4:8] == b"ftyp"
    if content_type == "video/webm":
        return data.startswith(b"\x1a\x45\xdf\xa3")
    return False


def _parse_embed(url: str):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(400, "Only HTTPS video URLs are allowed")
    host = parsed.netloc.lower().split(":", 1)[0]
    path = parsed.path.rstrip("/")
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        ref = ""
        if "v=" in parsed.query:
            ref = parsed.query.split("v=", 1)[1].split("&", 1)[0]
        if not ref and path.startswith("/shorts/"):
            ref = path.split("/", 2)[2] if len(path.split("/", 2)) == 3 else ""
        if not ref and path.startswith("/embed/"):
            ref = path.split("/", 2)[2] if len(path.split("/", 2)) == 3 else ""
        if not ref:
            raise HTTPException(400, "Invalid YouTube URL")
        return "youtube", ref
    if host == "youtu.be":
        ref = path.lstrip("/").split("/", 1)[0]
        if not ref:
            raise HTTPException(400, "Invalid YouTube URL")
        return "youtube", ref
    if host in {"vimeo.com", "www.vimeo.com", "player.vimeo.com"}:
        ref = path.rsplit("/", 1)[-1]
        if not ref.isdigit():
            raise HTTPException(400, "Invalid Vimeo URL")
        return "vimeo", ref
    if path.lower().endswith((".mp4", ".webm")):
        return "direct", url
    raise HTTPException(400, "URL must be YouTube, Vimeo, or a direct MP4/WebM HTTPS URL")


def _range(header: str | None, size: int):
    if not header:
        return 0, size - 1, False
    m = RANGE_RE.match(header.strip())
    if not m or size <= 0:
        raise HTTPException(416, "Invalid byte range", headers={"Content-Range": f"bytes */{size}"})
    a, b = m.groups()
    if not a:
        length = int(b) if b else 0
        if length <= 0:
            raise HTTPException(416, "Invalid byte range", headers={"Content-Range": f"bytes */{size}"})
        start, end = max(0, size - length), size - 1
    else:
        start = int(a)
        end = int(b) if b else size - 1
        if start >= size or start < 0:
            raise HTTPException(416, "Invalid byte range", headers={"Content-Range": f"bytes */{size}"})
        end = min(end, size - 1)
        if end < start:
            raise HTTPException(416, "Invalid byte range", headers={"Content-Range": f"bytes */{size}"})
    return start, end, True


def _part_key(upload_id: str, n: int) -> str:
    return f"tmp/profile-videos/{upload_id}/{n:06d}.part"


def _video_key(profile_slug: str, video_id: str, suffix: str) -> str:
    return f"profiles/{profile_slug}/{video_id}{suffix}"


@router.get("/public/{profile_slug}")
async def public_list(profile_slug: str, s: AsyncSession = Depends(db)):
    _profile(profile_slug)
    res = await s.execute(select(ProfileVideo).where(ProfileVideo.profile_slug == profile_slug, ProfileVideo.published.is_(True)).order_by(ProfileVideo.sort_order, ProfileVideo.created_at))
    return [{"id": v.id, "title": v.title, "description": v.description, "source_type": v.source_type, "embed_provider": v.embed_provider, "embed_ref": v.embed_ref, "stream_url": f"/api/v1/profile-videos/stream/{v.id}" if v.source_type == "upload" else None, "download_url": f"/api/v1/profile-videos/download/{v.id}" if v.source_type == "upload" else None, "content_type": v.content_type, "size": v.size} for v in res.scalars().all()]


@router.get("/download/{video_id}")
async def download(video_id: str, request: Request, s: AsyncSession = Depends(db)):
    v = await s.get(ProfileVideo, video_id)
    if not v or not v.published or v.source_type != "upload" or not v.object_key:
        raise HTTPException(404, "Video not found")
    try:
        stat = client.stat_object(BUCKET, v.object_key)
        size = stat.size
    except Exception as exc:
        raise HTTPException(404, "Video not found") from exc
    start, end, partial = _range(request.headers.get("range"), size)
    length = end - start + 1
    obj = client.get_object(BUCKET, v.object_key, offset=start, length=length)

    async def body():
        try:
            while True:
                chunk = obj.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            obj.close()
            obj.release_conn()

    filename = re.sub(r"[^A-Za-z0-9._-]+", "-", v.filename or f"{v.id}.mp4").strip("-") or f"{v.id}.mp4"
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "private, max-age=0, must-revalidate",
    }
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(body(), status_code=206 if partial else 200, media_type=v.content_type or "application/octet-stream", headers=headers)


@router.get("/stream/{video_id}")
async def stream(video_id: str, request: Request, s: AsyncSession = Depends(db)):
    v = await s.get(ProfileVideo, video_id)
    if not v or not v.published or v.source_type != "upload" or not v.object_key:
        raise HTTPException(404, "Video not found")
    try:
        stat = client.stat_object(BUCKET, v.object_key)
        size = stat.size
    except Exception as exc:
        raise HTTPException(404, "Video not found") from exc
    start, end, partial = _range(request.headers.get("range"), size)
    length = end - start + 1
    obj = client.get_object(BUCKET, v.object_key, offset=start, length=length)

    async def body():
        try:
            while True:
                chunk = obj.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            obj.close()
            obj.release_conn()

    headers = {"Accept-Ranges": "bytes", "Content-Length": str(length), "Cache-Control": "public, max-age=3600"}
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(body(), status_code=206 if partial else 200, media_type=v.content_type or "application/octet-stream", headers=headers)


@router.get("/admin/{profile_slug}")
async def admin_list(profile_slug: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    _profile(profile_slug)
    res = await s.execute(select(ProfileVideo).where(ProfileVideo.profile_slug == profile_slug).order_by(ProfileVideo.sort_order, ProfileVideo.created_at))
    return [{"id": v.id, "title": v.title, "description": v.description, "source_type": v.source_type, "embed_provider": v.embed_provider, "embed_ref": v.embed_ref, "content_type": v.content_type, "size": v.size, "published": v.published, "sort_order": v.sort_order} for v in res.scalars().all()]


@router.post("/uploads", status_code=201)
async def start_upload(payload: dict, user=Depends(admin), s: AsyncSession = Depends(db)):
    profile = _profile(payload.get("profile_slug", ""))
    title, filename = str(payload.get("title", "")).strip(), str(payload.get("filename", "")).strip()
    content_type = str(payload.get("content_type", "")).lower()
    try:
        size = int(payload.get("size", 0))
    except (TypeError, ValueError):
        raise HTTPException(400, "Invalid video size")
    description = payload.get("description")
    if description is not None:
        description = str(description).strip()
        if len(description) > 500:
            raise HTTPException(400, "Description must be 500 characters or fewer")
    if not title or len(title) > 200 or not filename or len(filename) > 255:
        raise HTTPException(400, "Valid title and filename are required")
    if content_type not in VIDEO_TYPES:
        raise HTTPException(415, "Only MP4 and WebM uploads are supported")
    if size <= 0 or size > MAX_BYTES:
        raise HTTPException(413, "Video must be between 1 byte and 500 MB")
    parts = (size + CHUNK_SIZE - 1) // CHUNK_SIZE
    try:
        if not client.bucket_exists(BUCKET):
            client.make_bucket(BUCKET)
    except Exception as exc:
        raise HTTPException(502, "Video storage is unavailable") from exc
    upload = ProfileVideoUpload(profile_slug=profile, title=title, description=description, filename=filename, content_type=content_type, size=size, total_parts=parts, created_by=user.get("sub", "unknown"))
    s.add(upload)
    await s.commit()
    return {"upload_id": upload.id, "chunk_size": CHUNK_SIZE, "total_parts": parts, "expires_at": (datetime.utcnow() + UPLOAD_TTL).isoformat() + "Z"}


@router.put("/uploads/{upload_id}/parts/{part_number}")
async def upload_part(upload_id: str, part_number: int, request: Request, user=Depends(admin), s: AsyncSession = Depends(db)):
    upload = await s.get(ProfileVideoUpload, upload_id)
    if not upload or upload.created_by != user.get("sub"):
        raise HTTPException(404, "Upload not found")
    if datetime.utcnow() - upload.created_at > UPLOAD_TTL:
        raise HTTPException(410, "Upload expired")
    if part_number < 1 or part_number > upload.total_parts or part_number > MAX_PARTS:
        raise HTTPException(400, "Invalid part number")
    data = await request.body()
    expected = min(CHUNK_SIZE, upload.size - (part_number - 1) * CHUNK_SIZE)
    if expected <= 0 or len(data) != expected:
        raise HTTPException(400, f"Part must be exactly {expected} bytes")
    if part_number == 1 and not _check_magic(upload.content_type, data):
        raise HTTPException(415, "Uploaded bytes do not match the declared video type")
    client.put_object(BUCKET, _part_key(upload_id, part_number), io.BytesIO(data), len(data), content_type=upload.content_type)
    return {"upload_id": upload_id, "part_number": part_number, "size": len(data)}


@router.post("/uploads/{upload_id}/complete", status_code=201)
async def complete_upload(upload_id: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    upload = await s.get(ProfileVideoUpload, upload_id)
    if not upload or upload.created_by != user.get("sub"):
        raise HTTPException(404, "Upload not found")
    if datetime.utcnow() - upload.created_at > UPLOAD_TTL:
        raise HTTPException(410, "Upload expired")
    parts, total = [], 0
    final_key = None
    try:
        for n in range(1, upload.total_parts + 1):
            key = _part_key(upload_id, n)
            st = client.stat_object(BUCKET, key)
            parts.append(CopySource(BUCKET, key))
            total += st.size
        if total != upload.size:
            raise HTTPException(400, "Incomplete upload")
        video_id = str(uuid.uuid4())
        final_key = _video_key(upload.profile_slug, video_id, VIDEO_TYPES[upload.content_type])
        if upload.total_parts == 1:
            source = client.get_object(BUCKET, _part_key(upload_id, 1))
            try:
                client.put_object(BUCKET, final_key, source, upload.size, content_type=upload.content_type)
            finally:
                source.close()
                source.release_conn()
        else:
            client.compose_object(BUCKET, final_key, parts)
        video = ProfileVideo(id=video_id, profile_slug=upload.profile_slug, title=upload.title, description=upload.description, source_type="upload", filename=upload.filename, object_key=final_key, content_type=upload.content_type, size=upload.size, created_by=user.get("sub", "unknown"))
        s.add(video)
        await s.delete(upload)
        await s.commit()
    except HTTPException:
        raise
    except Exception as exc:
        await s.rollback()
        if final_key:
            try: client.remove_object(BUCKET, final_key)
            except Exception: pass
        raise HTTPException(502, "Video composition failed") from exc
    finally:
        for n in range(1, upload.total_parts + 1):
            try: client.remove_object(BUCKET, _part_key(upload_id, n))
            except Exception: pass
    return {"id": video.id, "profile_slug": video.profile_slug, "title": video.title, "published": video.published}


@router.delete("/uploads/{upload_id}")
async def abort_upload(upload_id: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    upload = await s.get(ProfileVideoUpload, upload_id)
    if not upload or upload.created_by != user.get("sub"):
        raise HTTPException(404, "Upload not found")
    for n in range(1, upload.total_parts + 1):
        try: client.remove_object(BUCKET, _part_key(upload_id, n))
        except Exception: pass
    await s.delete(upload)
    await s.commit()
    return {"ok": True}


@router.post("/embeds", status_code=201)
async def add_embed(payload: dict, user=Depends(admin), s: AsyncSession = Depends(db)):
    profile = _profile(payload.get("profile_slug", ""))
    title = str(payload.get("title", "")).strip()
    if not title or len(title) > 200:
        raise HTTPException(400, "Valid title is required")
    provider, ref = _parse_embed(str(payload.get("url", "")).strip())
    video = ProfileVideo(profile_slug=profile, title=title, description=payload.get("description"), source_type="embed", embed_provider=provider, embed_ref=ref, created_by=user.get("sub", "unknown"))
    s.add(video)
    await s.commit()
    return {"id": video.id, "published": video.published, "embed_provider": provider, "embed_ref": ref}


@router.patch("/items/{video_id}")
async def update_item(video_id: str, payload: dict, user=Depends(admin), s: AsyncSession = Depends(db)):
    v = await s.get(ProfileVideo, video_id)
    if not v or v.profile_slug not in PROFILES:
        raise HTTPException(404, "Video not found")
    if "title" in payload:
        v.title = str(payload["title"]).strip()
        if not v.title or len(v.title) > 200: raise HTTPException(400, "Invalid title")
    for field in ("description", "published", "sort_order"):
        if field in payload: setattr(v, field, payload[field])
    v.updated_at = datetime.utcnow()
    await s.commit()
    return {"id": v.id, "profile_slug": v.profile_slug, "published": v.published}


@router.delete("/items/{video_id}")
async def delete_item(video_id: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    v = await s.get(ProfileVideo, video_id)
    if not v or v.profile_slug not in PROFILES:
        raise HTTPException(404, "Video not found")
    object_key = v.object_key
    await s.delete(v)
    await s.commit()
    if object_key:
        try: client.remove_object(BUCKET, object_key)
        except Exception: pass
    return {"ok": True}


@router.post("/reorder")
async def reorder(payload: dict, user=Depends(admin), s: AsyncSession = Depends(db)):
    profile = _profile(payload.get("profile_slug", ""))
    ids = payload.get("ids", [])
    if not isinstance(ids, list) or len(ids) > 100:
        raise HTTPException(400, "Invalid video order")
    res = await s.execute(select(ProfileVideo).where(ProfileVideo.profile_slug == profile, ProfileVideo.id.in_(ids)))
    videos = {v.id: v for v in res.scalars().all()}
    if len(videos) != len(ids):
        raise HTTPException(400, "Video order contains an invalid video")
    for i, video_id in enumerate(ids): videos[video_id].sort_order = i
    await s.commit()
    return {"ok": True}
