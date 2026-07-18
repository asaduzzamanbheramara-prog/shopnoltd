import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.core.db import Base


class TenantRoute(Base):
    __tablename__ = "tenant_routes"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    subdomain = Column(String(128), unique=True, nullable=False)
    tenant_id = Column(String(64), nullable=False, index=True)
    namespace = Column(String(64), nullable=False)
    plan = Column(String(64), default="free")
    storage_quota_gb = Column(Integer, default=10)
    user_quota = Column(Integer, default=10)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
