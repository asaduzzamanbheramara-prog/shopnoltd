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
    google = "google"  # Gemini — adapter stubbed, easy to fill in later
    azure_openai = "azure_openai"
    custom = "custom"  # any OpenAI-compatible endpoint (vLLM, LM Studio, etc.)


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider_type: Mapped[ProviderType] = mapped_column(
        Enum(ProviderType, name="provider_type_enum"), nullable=False
    )

    # Fernet-encrypted at the application layer — never store plaintext.
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
