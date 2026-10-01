from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

class OwnerCreate(BaseModel):
    display_name: str = Field(min_length=2,max_length=200)

class SiteCreate(BaseModel):
    domain: str = Field(min_length=3,max_length=253)

class ZoneCreate(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    width: int = Field(gt=0,le=4096)
    height: int = Field(gt=0,le=4096)

class CampaignCreate(BaseModel):
    name: str = Field(min_length=2,max_length=200)
    pricing_model: str = Field(pattern="^(CPM|CPC|CPA|FLAT)$")
    starts_at: datetime
    ends_at: datetime
    budget_minor: int = Field(ge=0,le=10_000_000_000)
    currency: str = Field(default="USD",pattern="^[A-Z]{3}$")

class CreativeCreate(BaseModel):
    campaign_id: str
    name: str = Field(min_length=1,max_length=200)
    asset_url: HttpUrl
    click_url: HttpUrl
    width: int = Field(gt=0,le=4096)
    height: int = Field(gt=0,le=4096)
    mime_type: str = Field(pattern="^(image/jpeg|image/png|image/webp|text/html)$")
