import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.db import Base


class FreeDomain(Base):
    __tablename__ = "freedomain"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), nullable=False, index=True)
    subdomain = Column(String(128), unique=True, nullable=False)
    target = Column(String(256), nullable=False)  # CNAME or A record target
    record_type = Column(String(8), default="CNAME")
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_check = Column(DateTime)
    last_status = Column(String(16))
