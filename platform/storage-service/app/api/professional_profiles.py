import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import ProfessionalProfile, ProfileVideo

router = APIRouter()
bearer = HTTPBearer(auto_error=False)
ALLOWED_VISIBILITY = {"private", "unlisted", "public"}
LIST_FIELDS = {"skills": 40, "experience": 30, "education": 20, "portfolio": 30}


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not creds:
        raise HTTPException(401, "Authentication required")
    try:
        user = await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc
    if not user.get("sub"):
        raise HTTPException(401, "Authenticated account has no subject identifier")
    return user


async def db():
    async with SessionLocal() as session:
        yield session


def _slug_for(subject: str) -> str:
    # Stable, non-identifying URL; never expose an email address or raw identity claim.
    return "member-" + uuid.uuid4().hex[:16]


def _serialize(profile: ProfessionalProfile, owner: bool = False):
    data = {
        "slug": profile.slug,
        "display_name": profile.display_name,
        "headline": profile.headline,
        "summary": profile.summary,
        "location": profile.location,
        "website": profile.website,
        "skills": profile.skills or [],
        "experience": profile.experience or [],
        "education": profile.education or [],
        "portfolio": profile.portfolio or [],
        "visibility": profile.visibility,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }
    if owner:
        data["profile_url"] = "/profile/" + profile.slug
    return data


def _bounded_text(payload: dict, key: str, current: str, limit: int) -> str:
    value = payload.get(key, current)
    if not isinstance(value, str):
        raise HTTPException(422, key + " must be text")
    value = value.strip()
    if len(value) > limit:
        raise HTTPException(422, key + " exceeds " + str(limit) + " characters")
    return value


def _bounded_list(payload: dict, key: str, current: list):
    value = payload.get(key, current or [])
    if not isinstance(value, list) or len(value) > LIST_FIELDS[key]:
        raise HTTPException(422, key + " must be a list with at most " + str(LIST_FIELDS[key]) + " entries")
    clean = []
    for item in value:
        if not isinstance(item, str):
            raise HTTPException(422, key + " entries must be text")
        item = item.strip()
        if not item or len(item) > 500:
            raise HTTPException(422, key + " entries must contain 1 to 500 characters")
        clean.append(item)
    return clean


@router.get("/directory")
async def public_directory(s: AsyncSession = Depends(db)):
    result = await s.execute(
        select(ProfessionalProfile)
        .where(ProfessionalProfile.visibility == "public")
        .order_by(ProfessionalProfile.updated_at.desc())
        .limit(100)
    )
    return [_serialize(profile, owner=False) for profile in result.scalars().all()]


@router.get("/me")
async def get_my_profile(user=Depends(current_user), s: AsyncSession = Depends(db)):
    subject = user["sub"]
    result = await s.execute(select(ProfessionalProfile).where(ProfessionalProfile.owner_sub == subject))
    profile = result.scalar_one_or_none()
    if profile is None:
        preferred = str(user.get("name") or user.get("preferred_username") or "Professional member").strip()
        preferred = preferred[:160] or "Professional member"
        profile = ProfessionalProfile(
            owner_sub=subject,
            slug=_slug_for(subject),
            display_name=preferred,
            headline="",
            summary="",
            visibility="private",
        )
        s.add(profile)
        try:
            await s.commit()
        except Exception:
            await s.rollback()
            result = await s.execute(select(ProfessionalProfile).where(ProfessionalProfile.owner_sub == subject))
            profile = result.scalar_one_or_none()
            if profile is None:
                raise HTTPException(409, "Could not provision professional profile; retry")
    return _serialize(profile, owner=True)


@router.put("/me")
async def update_my_profile(payload: dict, user=Depends(current_user), s: AsyncSession = Depends(db)):
    result = await s.execute(select(ProfessionalProfile).where(ProfessionalProfile.owner_sub == user["sub"]))
    profile = result.scalar_one_or_none()
    if profile is None:
        await get_my_profile(user=user, s=s)
        result = await s.execute(select(ProfessionalProfile).where(ProfessionalProfile.owner_sub == user["sub"]))
        profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(500, "Professional profile could not be initialized")

    profile.display_name = _bounded_text(payload, "display_name", profile.display_name, 160)
    if not profile.display_name:
        raise HTTPException(422, "display_name cannot be empty")
    profile.headline = _bounded_text(payload, "headline", profile.headline, 240)
    profile.summary = _bounded_text(payload, "summary", profile.summary, 3000)
    profile.location = _bounded_text(payload, "location", profile.location, 160)
    profile.website = _bounded_text(payload, "website", profile.website, 512)
    if profile.website and not re.match(r"^https://", profile.website, re.IGNORECASE):
        raise HTTPException(422, "website must use HTTPS")
    for field in LIST_FIELDS:
        setattr(profile, field, _bounded_list(payload, field, getattr(profile, field) or []))
    visibility = payload.get("visibility", profile.visibility)
    if visibility not in ALLOWED_VISIBILITY:
        raise HTTPException(422, "visibility must be private, unlisted, or public")
    profile.visibility = visibility
    profile.updated_at = datetime.utcnow()
    await s.commit()
    await s.refresh(profile)
    return _serialize(profile, owner=True)


@router.get("/share/{slug}", response_class=HTMLResponse)
async def share_profile(slug: str, s: AsyncSession = Depends(db)):
    result = await s.execute(select(ProfessionalProfile).where(ProfessionalProfile.slug == slug))
    profile = result.scalar_one_or_none()
    if profile is None or profile.visibility == "private":
        raise HTTPException(404, "Professional profile not found")

    videos_result = await s.execute(
        select(ProfileVideo)
        .where(ProfileVideo.profile_slug == slug, ProfileVideo.published.is_(True))
        .order_by(ProfileVideo.sort_order, ProfileVideo.created_at)
        .limit(1)
    )
    video = videos_result.scalar_one_or_none()
    title_text = profile.display_name + ((" — " + profile.headline) if profile.headline else "") + " | Shopnoltd"
    description_text = (profile.summary or profile.headline or "Professional profile on Shopnoltd.")[:300]
    canonical = "https://shopnoltd.dpdns.org/profile/" + profile.slug
    destination = "/profile-view/" + profile.slug
    image_url = "https://shopnoltd.dpdns.org/logo.svg"
    video_url = ""
    video_type = ""
    if video:
        if video.source_type == "upload":
            video_url = "https://storage-service.shopnoltd.dpdns.org/api/v1/profile-videos/stream/" + video.id
            video_type = video.content_type or ""
        elif video.embed_provider == "youtube":
            video_url = "https://www.youtube.com/embed/" + video.embed_ref
        elif video.embed_provider == "vimeo":
            video_url = "https://player.vimeo.com/video/" + video.embed_ref
        elif video.embed_provider == "direct":
            video_url = video.embed_ref or ""
            video_type = "video/mp4" if video_url.lower().split("?", 1)[0].endswith(".mp4") else "video/webm"

    from html import escape
    title = escape(title_text, quote=True)
    description = escape(description_text, quote=True)
    canonical_html = escape(canonical, quote=True)
    image_html = escape(image_url, quote=True)
    video_html = escape(video_url, quote=True)
    video_tags = ""
    twitter_card = "summary_large_image"
    if video_url:
        twitter_card = "player"
        video_tags = (
            '<meta property="og:video" content="' + video_html + '">'
            '<meta property="og:video:secure_url" content="' + video_html + '">'
            '<meta property="og:video:type" content="' + escape(video_type or "text/html", quote=True) + '">'
            '<meta property="og:video:width" content="1280">'
            '<meta property="og:video:height" content="720">'
            '<meta name="twitter:player" content="' + video_html + '">'
            '<meta name="twitter:player:width" content="1280">'
            '<meta name="twitter:player:height" content="720">'
        )
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>' + title + '</title>'
        '<meta name="description" content="' + description + '">'
        '<link rel="canonical" href="' + canonical_html + '">'
        '<meta property="og:type" content="profile">'
        '<meta property="og:url" content="' + canonical_html + '">'
        '<meta property="og:title" content="' + title + '">'
        '<meta property="og:description" content="' + description + '">'
        '<meta property="og:image" content="' + image_html + '">'
        '<meta name="twitter:card" content="' + twitter_card + '">'
        '<meta name="twitter:title" content="' + title + '">'
        '<meta name="twitter:description" content="' + description + '">'
        '<meta name="twitter:image" content="' + image_html + '">'
        + video_tags +
        '<meta http-equiv="refresh" content="0;url=' + escape(destination, quote=True) + '">'
        '</head><body><main><h1>' + title + '</h1><p>' + description + '</p>'
        '<p><a href="' + escape(destination, quote=True) + '">Open complete professional profile and videos</a></p>'
        '<script>window.location.replace(' + repr(destination) + ')</script>'
        '</main></body></html>'
    )
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "public, max-age=60", "X-Robots-Tag": "noindex"},
    )


@router.get("/{slug}")
async def get_public_profile(slug: str, s: AsyncSession = Depends(db)):
    result = await s.execute(select(ProfessionalProfile).where(ProfessionalProfile.slug == slug))
    profile = result.scalar_one_or_none()
    if profile is None or profile.visibility == "private":
        raise HTTPException(404, "Professional profile not found")
    return _serialize(profile, owner=False)
