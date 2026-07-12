from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
import uuid
from datetime import datetime
from app.core.db import Base
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    type = Column(String(16), default="direct")  # direct, group
    title = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)
class Participant(Base):
    __tablename__ = "participants"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    role = Column(String(16), default="member")
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_read_at = Column(DateTime)
    __table_args__ = (Index("ix_part_conv_user", "conversation_id", "user_id", unique=True),)
class Message(Base):
    __tablename__ = "messages"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(String(64), nullable=False, index=True)
    body = Column(Text, nullable=False)
    attachments = Column(String, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    edited_at = Column(DateTime)
    deleted_at = Column(DateTime)
