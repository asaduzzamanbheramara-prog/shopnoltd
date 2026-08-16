from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProxyCreate(BaseModel):
    label: str
    server: str = Field(..., description="host:port")
    username: str | None = None
    password: str | None = None
    country: str | None = None


class ProxyOut(BaseModel):
    id: UUID
    label: str
    server: str
    country: str | None = None

    class Config:
        from_attributes = True


class ProfileCreate(BaseModel):
    name: str
    purpose: str = Field("qa", description="qa | staff | scraping")
    owner: str | None = None
    notes: str | None = None
    proxy_id: UUID | None = None


class ProfileOut(BaseModel):
    id: UUID
    name: str
    purpose: str
    owner: str | None
    is_active: bool
    proxy_id: UUID | None
    created_at: datetime
    last_used_at: datetime | None

    class Config:
        from_attributes = True


class SessionLaunchRequest(BaseModel):
    profile_id: UUID
    target_url: str = Field(..., description="URL to open, e.g. a shopnoltd.dpdns.org service")
    headless: bool = True


class SessionLaunchResponse(BaseModel):
    profile_id: UUID
    status: str
    debug_ws_endpoint: str | None = None
    message: str | None = None
