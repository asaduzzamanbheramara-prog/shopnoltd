from datetime import datetime
from pydantic import BaseModel, Field


class AutomationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    trigger_type: str
    trigger_config: dict = Field(default_factory=dict)
    action_type: str
    action_config: dict = Field(default_factory=dict)
    max_retries: int = Field(default=3, ge=0, le=10)
    next_run_at: datetime | None = None


class AutomationOut(AutomationCreate):
    id: str
    tenant_id: str
    owner_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventIn(BaseModel):
    event_type: str
    idempotency_key: str = Field(min_length=1, max_length=255)
    payload: dict = Field(default_factory=dict)
