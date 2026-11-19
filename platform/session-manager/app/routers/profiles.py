import os
import shutil
import uuid
from pathlib import Path
from app.auth import require_user
from app.models.db import Profile, get_db
from app.models.schemas import ProfileCreate, ProfileOut
from app.services.session_pool import pool
from app.routers.viewer import revoke_profile_viewers
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("", response_model=list[ProfileOut])
def list_profiles(user=Depends(require_user), db: Session = Depends(get_db)):
    return db.query(Profile).filter(Profile.owner == user["sub"]).all()

@router.post("", response_model=ProfileOut)
def create_profile(payload: ProfileCreate, user=Depends(require_user), db: Session = Depends(get_db)):
    if payload.proxy_id is not None:
        raise HTTPException(409, "Proxy assignment is disabled until proxy ownership is enforced")
    profile_id = uuid.uuid4()
    profile = Profile(id=profile_id, name=payload.name, purpose=payload.purpose, owner=user["sub"], notes=payload.notes, proxy_id=None, user_data_dir=f"profiles/{profile_id}")
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: str, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.owner == user["sub"]).first()
    if not profile:
        raise HTTPException(404, "Profile not found")
    return profile

@router.delete("/{profile_id}")
async def delete_profile(profile_id: str, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.owner == user["sub"]).first()
    if profile:
        await pool.close(profile_id)
        revoke_profile_viewers(profile_id)
        storage_root = Path(os.getenv("PROFILE_STORAGE_ROOT", "/data")).resolve()
        profile_path = (storage_root / profile.user_data_dir).resolve()
        if profile_path != storage_root and storage_root in profile_path.parents and profile_path.exists():
            shutil.rmtree(profile_path)
        db.delete(profile)
        db.commit()
    return {"deleted": bool(profile)}
