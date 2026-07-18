import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.core.db import Base


class Report(Base):
    __tablename__ = "reports"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    kind = Column(String(32), default="pdf")  # pdf, csv
    query_sql = Column(String)
    status = Column(String(16), default="queued")
    file_path = Column(String(512))
    created_at = Column(DateTime, default=datetime.utcnow)
