from datetime import datetime

from pydantic import BaseModel


class DonorIn(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    is_anonymous: bool = False


class CampaignIn(BaseModel):
    name: str
    description: str = ""
    goal_amount: float = 0
    ends_at: datetime | None = None


class DonationIn(BaseModel):
    donor_id: str
    campaign_id: str = ""
    amount: float
    currency: str = "USD"
    method: str = "stripe"


class GrantIn(BaseModel):
    name: str
    funder: str = ""
    amount: float = 0
    currency: str = "USD"
    description: str = ""
    deadline: datetime | None = None


class BeneficiaryIn(BaseModel):
    name: str
    type: str = "individual"
    location: str = ""
    notes: str = ""
