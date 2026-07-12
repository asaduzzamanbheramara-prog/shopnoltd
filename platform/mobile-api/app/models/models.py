from sqlalchemy import Column, String, DateTime, Integer, JSON
import uuid
from datetime import datetime
from app.core.db import Base
class AppRelease(Base):
    __tablename__ = "app_releases"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), nullable=False, index=True)  # shopno-survey, shopno-chat, ...
    version = Column(String(32), nullable=False)  # 1.0.0
    build = Column(Integer, nullable=False, default=1)
    apk_path = Column(String(512))
    sha256 = Column(String(128))
    size_bytes = Column(Integer)
    min_os_version = Column(String(16), default="8.0")
    release_notes = Column(String)
    force_update = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
class AppConfig(Base):
    __tablename__ = "app_config"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), unique=True, nullable=False)
    data = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
