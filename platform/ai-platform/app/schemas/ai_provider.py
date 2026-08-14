import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import ProviderType

# ---------- Provider ----------


class ProviderCreate(BaseModel):
    name: str
    provider_type: ProviderType
    api_key: str | None = Field(
        default=None, description="Plaintext on input only; encrypted before storage."
    )
    base_url: str | None = None
    is_active: bool = True
    extra_config: dict = Field(default_factory=dict)


class ProviderUpdate(BaseModel):
    name: str | None = None
    api_key: str | None = None  # if provided, replaces the stored (encrypted) key
    base_url: str | None = None
    is_active: bool | None = None
    extra_config: dict | None = None


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    provider_type: ProviderType
    base_url: str | None
    is_active: bool
    api_key_masked: str | None = None  # never the real key
    extra_config: dict
    created_at: datetime
    updated_at: datetime


# ---------- Model ----------


class ModelCreate(BaseModel):
    model_name: str
    display_name: str
    is_active: bool = False
    is_default: bool = False
    capabilities: dict = Field(default_factory=dict)
    priority: int = 100


class ModelUpdate(BaseModel):
    display_name: str | None = None
    capabilities: dict | None = None
    priority: int | None = None


class ModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_id: uuid.UUID
    model_name: str
    display_name: str
    is_active: bool
    is_default: bool
    capabilities: dict
    priority: int
    created_at: datetime
    updated_at: datetime


class ModelWithProviderOut(ModelOut):
    provider_name: str
    provider_type: ProviderType
