import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.core.db import Base


class Event(Base):
    __tablename__ = "events"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    owner_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text)
    venue = Column(String(256))
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    timezone = Column(String(64), default="UTC")
    capacity = Column(Integer, default=100)
    is_online = Column(Boolean, default=False)
    cover_image = Column(String(512))
    created_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = "event_sessions"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(64), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    description = Column(Text)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    track = Column(String(64))
    room = Column(String(64))


class Ticket(Base):
    __tablename__ = "event_tickets"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128))  # attendee name
    email = Column(String(256))
    qr_code = Column(Text)  # base64
    status = Column(String(16), default="valid")  # valid, used, cancelled
    price = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Speaker(Base):
    __tablename__ = "event_speakers"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    bio = Column(Text)
    photo = Column(String(512))
    company = Column(String(128))
