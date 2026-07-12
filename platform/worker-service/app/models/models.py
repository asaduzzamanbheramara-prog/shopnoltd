from sqlalchemy import Column, String, DateTime, JSON, Integer
import uuid
from datetime import datetime
from app.core.db import Base
class Task(Base):
    __tablename__ = "tasks"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False, index=True)
    args = Column(JSON, default=dict)
    status = Column(String(16), default="queued", index=True)  # queued, running, done, failed
    result = Column(JSON)
    error = Column(String)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
