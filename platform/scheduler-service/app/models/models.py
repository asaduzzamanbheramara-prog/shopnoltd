import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String

from app.core.db import Base


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), unique=True, nullable=False)
    cron = Column(String(64), nullable=False)  # "*/5 * * * *"
    url = Column(String(512), nullable=False)
    method = Column(String(8), default="POST")
    body = Column(JSON, default=dict)
    active = Column(Integer, default=1)
    last_run = Column(DateTime)
    last_status = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
