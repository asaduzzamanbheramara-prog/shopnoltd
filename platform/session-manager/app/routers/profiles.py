import uuid

from app.models.db import Profile, get_db
from app.models.schemas import ProfileCreate, ProfileOut
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=list[ProfileOut])
def list_profiles(db: Session = Depends(get_db)):
    return db.query(Profile).all()


@router.post("", response_model=ProfileOut)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        name=payload.name,
        purpose=payload.purpose,
        owner=payload.owner,
        notes=payload.notes,
        proxy_id=payload.proxy_id,
        user_data_dir=f"profiles/{profile_id}",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(404, "Profile not found")
    return profile


@router.delete("/{profile_id}")
def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if profile:
        db.delete(profile)
        db.commit()
    return {"deleted": bool(profile)}
