import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String

from app.core.db import Base


class Event(Base):
    __tablename__ = "events"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), index=True)
    name = Column(String(128), nullable=False, index=True)
    properties = Column(String, default="{}")
    source = Column(String(64), index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    __table_args__ = (Index("ix_event_tenant_name_time", "tenant_id", "name", "created_at"),)
