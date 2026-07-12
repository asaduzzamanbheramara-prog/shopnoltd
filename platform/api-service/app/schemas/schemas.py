from pydantic import BaseModel
class HealthAll(BaseModel):
    api_service: str
    auth: str
    payment: str
    billing: str
    exchange: str
    social: str
    messaging: str
    notification: str
    storage: str
