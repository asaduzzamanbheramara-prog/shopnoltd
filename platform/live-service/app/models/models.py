from sqlalchemy import Column, String, DateTime, Boolean, Integer
import uuid
from datetime import datetime
from app.core.db import Base
class Stream(Base):
    __tablename__ = "streams"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    owner_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False, unique=True)
    title = Column(String(256))
    description = Column(String(2000))
    offline_banner = Column(String(256))
    recording_enabled = Column(Boolean, default=True)
    is_live = Column(Boolean, default=False)
    viewer_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
