from pydantic import BaseModel
from datetime import datetime
class LicenseIn(BaseModel):
    plan: str; features: dict = {}; seats: int = 1; expires_at: datetime
class LicenseOut(BaseModel):
    key: str; plan: str; seats: int; expires_at: datetime; features: dict
