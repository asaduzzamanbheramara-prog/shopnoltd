import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import require_user
from app.models.db import Profile, get_db
from app.models.schemas import (
    SessionLaunchRequest,
    SessionLaunchResponse,
    TabNavigateRequest,
    TabOpenRequest,
)
from app.routers.viewer import revoke_profile_viewers
from app.services.session_pool import pool

router = APIRouter()
STORAGE_ROOT = Path(os.getenv("PROFILE_STORAGE_ROOT", "/data"))


def _owned_profile(profile_id: str, owner: str, db: Session) -> Profile:
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.owner == owner).first()
    if not profile:
        raise HTTPException(404, "Profile not found")
    return profile


def _profile_storage_path(profile: Profile) -> Path:
    root = STORAGE_ROOT.resolve()
    path = (root / profile.user_data_dir).resolve()
    if path == root or root not in path.parents:
        raise HTTPException(409, "Profile storage path is outside the managed data directory")
    return path


@router.post("/launch", response_model=SessionLaunchResponse)
async def launch_session(payload: SessionLaunchRequest, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = _owned_profile(str(payload.profile_id), user["sub"], db)
    profile_path = _profile_storage_path(profile)
    profile_path.mkdir(parents=True, exist_ok=True)
    try:
        result = await pool.get_or_launch(
            profile_id=str(profile.id),
            user_data_dir=str(profile_path),
            target_url=payload.target_url,
            proxy=profile.proxy,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    profile.last_used_at = datetime.utcnow()
    db.commit()
    return SessionLaunchResponse(
        profile_id=profile.id,
        status=result["status"],
        tab_id=result["tab_id"],
        message="Browser session launched. Open the authenticated viewer to control this session.",
    )


@router.get("/{profile_id}/tabs")
async def list_tabs(profile_id: str, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = _owned_profile(profile_id, user["sub"], db)
    return {"tabs": await pool.list_tabs(str(profile.id))}


@router.post("/{profile_id}/tabs")
async def open_tab(profile_id: str, payload: TabOpenRequest, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = _owned_profile(profile_id, user["sub"], db)
    try:
        tab = await pool.open_tab(str(profile.id), payload.target_url)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    profile.last_used_at = datetime.utcnow()
    db.commit()
    return tab


@router.post("/{profile_id}/tabs/{tab_id}/navigate")
async def navigate_tab(profile_id: str, tab_id: str, payload: TabNavigateRequest, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = _owned_profile(profile_id, user["sub"], db)
    try:
        tab = await pool.navigate_tab(str(profile.id), tab_id, payload.target_url)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    profile.last_used_at = datetime.utcnow()
    db.commit()
    return tab


@router.post("/{profile_id}/tabs/{tab_id}/focus")
async def focus_tab(profile_id: str, tab_id: str, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = _owned_profile(profile_id, user["sub"], db)
    if not await pool.focus_tab(str(profile.id), tab_id):
        raise HTTPException(404, "Browser tab not found")
    return {"focused": True}


@router.delete("/{profile_id}/tabs/{tab_id}")
async def close_tab(profile_id: str, tab_id: str, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = _owned_profile(profile_id, user["sub"], db)
    if not await pool.close_tab(str(profile.id), tab_id):
        raise HTTPException(404, "Browser tab not found")
    revoke_profile_viewers(profile_id)
    return {"closed": True}


@router.get("/{profile_id}/downloads")
def list_downloads(profile_id: str, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = _owned_profile(profile_id, user["sub"], db)
    return {"downloads": pool.list_downloads(str(_profile_storage_path(profile)))}


@router.get("/{profile_id}/downloads/{download_id}")
def get_download(profile_id: str, download_id: str, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = _owned_profile(profile_id, user["sub"], db)
    try:
        path, filename = pool.get_download(str(_profile_storage_path(profile)), download_id)
    except FileNotFoundError:
        raise HTTPException(404, "Download not found")
    return FileResponse(path, filename=filename, media_type="application/octet-stream")


@router.post("/{profile_id}/close")
async def close_session(profile_id: str, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = _owned_profile(profile_id, user["sub"], db)
    if not await pool.close(str(profile.id)):
        raise HTTPException(404, "No active session for this profile")
    revoke_profile_viewers(profile_id)
    return {"closed": True}


@router.get("/active")
def list_active_sessions(user=Depends(require_user), db: Session = Depends(get_db)):
    owned_ids = {str(row[0]) for row in db.query(Profile.id).filter(Profile.owner == user["sub"]).all()}
    return {key: value for key, value in pool.list_active().items() if key in owned_ids}
