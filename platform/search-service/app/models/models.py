import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.db import Base


class Index(Base):
    __tablename__ = "indexes"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(64), nullable=False, unique=True)
    doc_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
