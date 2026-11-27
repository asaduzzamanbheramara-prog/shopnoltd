import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProviderType(enum.StrEnum):
    openai = "openai"
    anthropic = "anthropic"
    ollama = "ollama"
    google = "google"  # Gemini Î“Ã‡Ã¶ adapter stubbed, easy to fill in later
    azure_openai = "azure_openai"
    custom = "custom"  # any OpenAI-compatible endpoint (vLLM, LM Studio, etc.)


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider_type: Mapped[ProviderType] = mapped_column(
        Enum(ProviderType, name="provider_type_enum"), nullable=False
    )

    # Fernet-encrypted at the application layer Î“Ã‡Ã¶ never store plaintext.
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    base_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # e.g. Ollama host, Azure endpoint
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    extra_config: Mapped[dict] = mapped_column(JSONB, default=dict)  # org id, api version, etc.

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    models: Mapped[list["AIModel"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class AIModel(Base):
    __tablename__ = "ai_models"
    __table_args__ = (UniqueConstraint("provider_id", "model_name", name="uq_provider_model"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_providers.id", ondelete="CASCADE"), nullable=False
    )

    model_name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )  # e.g. "gpt-4o", "claude-sonnet-4-6"
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # used when no model specified

    capabilities: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # {"chat": true, "embeddings": false, "context_window": 128000}
    priority: Mapped[int] = mapped_column(
        Integer, default=100
    )  # lower = preferred, for fallback ordering

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    provider: Mapped["AIProvider"] = relationship(back_populates="models")


class AIConnection(Base):
    __tablename__ = "ai_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "name", name="uq_ai_connection_user_kind_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)  # github | local
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_test_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AIChatThread(Base):
    """Durable, tenant- and user-owned AI Workspace conversation snapshot."""

    __tablename__ = "ai_chat_threads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="New chat")
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    messages: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True
    )


class AIPersonalMemory(Base):
    """Explicitly user-authored memory, separately reviewable and deletable."""

    __tablename__ = "ai_personal_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="general")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True
    )

class AIPersonalMemorySettings(Base):
    """Per-account memory consent switch; saved items remain reviewable when paused."""

    __tablename__ = "ai_personal_memory_settings"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    memory_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class Agent(Base):
    """Agent table registered on the same metadata initialized by the AI Platform lifespan.

    Column names and types intentionally match the pre-existing legacy table so
    create_all() is additive and does not require a destructive table rebuild.
    """
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(
        Text, default="You are a helpful Shopnoltd assistant."
    )
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Conversation(Base):
    """Conversation rows retain the legacy ai_conversations schema."""
    __tablename__ = "ai_conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agents.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(String(16), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
