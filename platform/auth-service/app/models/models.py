from sqlalchemy import Column, String, DateTime, Boolean
import uuid
from datetime import datetime
from app.core.db import Base
class Session(Base):
    __tablename__ = "sessions"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), nullable=False, index=True)
    ip = Column(String(64))
    user_agent = Column(String(256))
    device = Column(String(64))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime)
