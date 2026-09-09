import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from app.core.db import Base

class WorkTaskConfig(Base):
    __tablename__ = "work_task_configs"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    work_id = Column(String(64), ForeignKey("works.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    task_url = Column(Text, nullable=True)
    media_url = Column(Text, nullable=True)
    media_type = Column(String(32), nullable=False, default="none")
    required_watch_seconds = Column(Integer, nullable=False, default=0)
    watch_rate_per_minute = Column(Numeric(20, 8), nullable=False, default=0)
    rate_currency = Column(String(16), nullable=False, default="BDT")
    rate_rules = Column(Text, nullable=True)
    social_rates = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkSession(Base):
    __tablename__ = "work_sessions"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    work_id = Column(String(64), ForeignKey("works.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(128), nullable=False, index=True)
    stage = Column(String(24), nullable=False, default="before", index=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    last_heartbeat_at = Column(DateTime, nullable=True)
    work_seconds = Column(Integer, nullable=False, default=0)
    watch_seconds = Column(Integer, nullable=False, default=0)
    interaction_seconds = Column(Integer, nullable=False, default=0)
    eligible_watch_seconds = Column(Integer, nullable=False, default=0)
    calculated_amount = Column(Numeric(20, 8), nullable=False, default=0)
    currency = Column(String(16), nullable=False, default="BDT")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (Index("ix_work_session_worker_work", "worker_id", "work_id"),)

class WorkEvidence(Base):
    __tablename__ = "work_evidence"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(64), ForeignKey("work_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    work_id = Column(String(64), ForeignKey("works.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(128), nullable=False, index=True)
    kind = Column(String(32), nullable=False, index=True)
    title = Column(String(300), nullable=True)
    evidence_url = Column(Text, nullable=True)
    data_url = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    deleted_at = Column(DateTime, nullable=True)

class WorkEvent(Base):
    __tablename__ = "work_events"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(64), ForeignKey("work_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    work_id = Column(String(64), ForeignKey("works.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(128), nullable=False, index=True)
    event_type = Column(String(48), nullable=False, index=True)
    event_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    duration_seconds = Column(Integer, nullable=False, default=0)
    rate_basis = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=True)
