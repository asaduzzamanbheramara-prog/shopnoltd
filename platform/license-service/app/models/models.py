import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String

from app.core.db import Base


class License(Base):
    __tablename__ = "licenses"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    key = Column(String(128), unique=True, nullable=False)
    plan = Column(String(64), nullable=False)
    features = Column(JSON, default=dict)
    seats = Column(Integer, default=1)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
