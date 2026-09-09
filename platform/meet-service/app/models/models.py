import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.core.db import Base


class Room(Base):
    __tablename__ = "rooms"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False, unique=True)
    owner_id = Column(String(64), nullable=False, index=True)
    password_hash = Column(String(256))
    is_recording = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)


class Participant(Base):
    __tablename__ = "room_participants"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String(64), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    role = Column(String(16), default="member")
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime)


class CallSession(Base):
    __tablename__ = "call_sessions"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    room_id = Column(String(64), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    initiator_id = Column(String(64), nullable=False, index=True)
    call_type = Column(String(16), nullable=False, default="video")
    state = Column(String(16), nullable=False, default="ringing")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    answered_at = Column(DateTime)
    ended_at = Column(DateTime)
