import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.core.db import Base


class Document(Base):
    __tablename__ = "documents"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    title = Column(String(256))
    source_uri = Column(String(512))
    text = Column(Text)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    idx = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    # embedding stored as pgvector bytea in production; for simplicity keep as JSON
    embedding = Column(String)


class Agent(Base):
    __tablename__ = "agents"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    system_prompt = Column(Text, default="You are a helpful Shopnoltd assistant.")
    model = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "ai_conversations"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(64), ForeignKey("agents.id"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    role = Column(String(16))  # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
