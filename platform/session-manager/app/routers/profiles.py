import uuid
from app.auth import require_user
from app.models.db import Profile, get_db
from app.models.schemas import ProfileCreate, ProfileOut
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
def delete_profile(profile_id: str, user=Depends(require_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.owner == user["sub"]).first()
    if profile:
        db.delete(profile)
        db.commit()
    return {"deleted": bool(profile)}
