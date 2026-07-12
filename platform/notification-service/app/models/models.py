from sqlalchemy import Column, String, DateTime, JSON, Enum, Text
import uuid, enum
from datetime import datetime
from app.core.db import Base
class NStatus(str, enum.Enum): pending="pending"; sent="sent"; failed="failed"; queued="queued"
class NChannel(str, enum.Enum): email="email"; sms="sms"; push="push"; webhook="webhook"
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    channel = Column(Enum(NChannel), nullable=False)
    status = Column(Enum(NStatus), default=NStatus.queued, index=True)
    subject = Column(String(256))
    body = Column(Text, nullable=False)
    recipient = Column(String(256), nullable=False)
    meta = Column(JSON, default=dict)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime)
class Template(Base):
    __tablename__ = "templates"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    channel = Column(Enum(NChannel), nullable=False)
    subject = Column(String(256))
    body = Column(Text, nullable=False)
    locale = Column(String(8), default="en")
    variables = Column(JSON, default=list)
