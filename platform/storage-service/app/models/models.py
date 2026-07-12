from sqlalchemy import Column, String, DateTime, Integer
import uuid
from datetime import datetime
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
