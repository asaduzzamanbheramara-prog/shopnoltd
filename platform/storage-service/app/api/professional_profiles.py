import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import ProfessionalProfile

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


@router.get("/{slug}")
async def get_public_profile(slug: str, s: AsyncSession = Depends(db)):
    result = await s.execute(select(ProfessionalProfile).where(ProfessionalProfile.slug == slug))
    profile = result.scalar_one_or_none()
    if profile is None or profile.visibility == "private":
        raise HTTPException(404, "Professional profile not found")
    return _serialize(profile, owner=False)
