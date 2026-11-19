import os
from datetime import datetime
from pathlib import Path
from app.auth import require_user
from app.models.db import Profile, get_db
from app.models.schemas import SessionLaunchRequest, SessionLaunchResponse
from app.services.session_pool import pool
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter()
STORAGE_ROOT = Path(os.getenv("PROFILE_STORAGE_ROOT", "/data"))

@router.post("/launch", response_model=SessionLaunchResponse)
async def launch_session(payload: SessionLaunchRequest, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == payload.profile_id, Profile.owner == user["sub"]).first()
    if not profile:
        raise HTTPException(404, "Profile not found")
    profile_path = STORAGE_ROOT / profile.user_data_dir
    profile_path.mkdir(parents=True, exist_ok=True)
    result = await pool.get_or_launch(profile_id=str(profile.id), user_data_dir=str(profile_path), target_url=payload.target_url, proxy=profile.proxy)
    profile.last_used_at = datetime.utcnow()
    db.commit()
    return SessionLaunchResponse(profile_id=profile.id, status=result["status"], message="Browser session launched. Live viewing is disabled until an authenticated viewer is available.")

@router.post("/{profile_id}/close")
async def close_session(profile_id: str, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.owner == user["sub"]).first()
    if not profile:
        raise HTTPException(404, "Profile not found")
    if not await pool.close(profile_id):
        raise HTTPException(404, "No active session for this profile")
    return {"closed": True}

@router.get("/active")
def list_active_sessions(user=Depends(require_user), db: Session = Depends(get_db)):
    owned_ids = {str(row[0]) for row in db.query(Profile.id).filter(Profile.owner == user["sub"]).all()}
    return {key: value for key, value in pool.list_active().items() if key in owned_ids}
