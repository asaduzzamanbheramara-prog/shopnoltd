from sqlalchemy import Column, String, DateTime, Integer, Boolean
import uuid
from datetime import datetime
from app.core.db import Base
class Domain(Base):
    __tablename__ = "domains"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), unique=True, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
class Mailbox(Base):
    __tablename__ = "mailboxes"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    domain_id = Column(String(64), nullable=False, index=True)
    local_part = Column(String(64), nullable=False)
    full_address = Column(String(256), unique=True, nullable=False)
    quota_mb = Column(Integer, default=1024)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
class Message(Base):
    __tablename__ = "mail_messages"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mailbox_id = Column(String(64), nullable=False, index=True)
    from_addr = Column(String(256), nullable=False)
    to_addrs = Column(String, default=list)
    subject = Column(String(512))
    body = Column(String)
    folder = Column(String(32), default="INBOX")
    read = Column(Boolean, default=False)
    received_at = Column(DateTime, default=datetime.utcnow, index=True)
