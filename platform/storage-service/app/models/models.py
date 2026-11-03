import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String

from app.core.db import Base


class Bucket(Base):
    __tablename__ = "buckets"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(64), nullable=False, unique=True)
    purpose = Column(String(64), default="general")
    created_at = Column(DateTime, default=datetime.utcnow)


class Object(Base):
    __tablename__ = "objects"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    bucket_id = Column(String(64), nullable=False, index=True)
    key = Column(String(512), nullable=False)
    size = Column(Integer, default=0)
    content_type = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ProfileVideo(Base):
    __tablename__ = "profile_videos"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_slug = Column(String(64), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500))
    source_type = Column(String(16), nullable=False)
    filename = Column(String(255))
    object_key = Column(String(512))
    content_type = Column(String(64))
    size = Column(BigInteger, default=0)
    embed_provider = Column(String(16))
    embed_ref = Column(String(1024))
    sort_order = Column(Integer, nullable=False, default=0)
    published = Column(Boolean, nullable=False, default=False)
    created_by = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProfileVideoUpload(Base):
    __tablename__ = "profile_video_uploads"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_slug = Column(String(64), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500))
    filename = Column(String(255), nullable=False)
    content_type = Column(String(64), nullable=False)
    size = Column(BigInteger, nullable=False)
    total_parts = Column(Integer, nullable=False)
    created_by = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)



class ProfessionalProfile(Base):
    __tablename__ = "professional_profiles"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_sub = Column(String(128), nullable=False, unique=True, index=True)
    slug = Column(String(64), nullable=False, unique=True, index=True)
    display_name = Column(String(160), nullable=False)
    headline = Column(String(240), nullable=False, default="")
    summary = Column(String(3000), nullable=False, default="")
    location = Column(String(160), nullable=False, default="")
    website = Column(String(512), nullable=False, default="")
    skills = Column(__import__("sqlalchemy").JSON, nullable=False, default=list)
    experience = Column(__import__("sqlalchemy").JSON, nullable=False, default=list)
    education = Column(__import__("sqlalchemy").JSON, nullable=False, default=list)
    portfolio = Column(__import__("sqlalchemy").JSON, nullable=False, default=list)
    visibility = Column(String(16), nullable=False, default="private")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
