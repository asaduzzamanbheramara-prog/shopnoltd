import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String, Text

from app.core.db import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(64), index=True)
    action = Column(String(128), nullable=False, index=True)
    resource = Column(String(128))
    resource_id = Column(String(128))
    ip = Column(String(64))
    user_agent = Column(String(256))
    data = Column(Text, default="{}")
    prev_hash = Column(String(64))
    hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    __table_args__ = (Index("ix_audit_tenant_time", "tenant_id", "created_at"),)
