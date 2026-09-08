import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text

from app.core.db import Base


class Work(Base):
    __tablename__ = "works"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    creator_id = Column(String(128), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    reward_amount = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(16), nullable=False, default="BDT")
    max_workers = Column(Integer, nullable=False, default=1)
    deadline = Column(DateTime, nullable=True)
    status = Column(String(24), nullable=False, default="open", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class WorkAssignment(Base):
    __tablename__ = "work_assignments"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    work_id = Column(String(64), ForeignKey("works.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(128), nullable=False, index=True)
    status = Column(String(24), nullable=False, default="active", index=True)
    accepted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (Index("ix_work_assignment_pair", "work_id", "worker_id", unique=True),)


class WorkSubmission(Base):
    __tablename__ = "work_submissions"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    work_id = Column(String(64), ForeignKey("works.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(128), nullable=False, index=True)
    proof = Column(Text, nullable=False)
    status = Column(String(24), nullable=False, default="pending", index=True)
    reviewer_id = Column(String(128), nullable=True)
    review_note = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    reviewed_at = Column(DateTime, nullable=True)
