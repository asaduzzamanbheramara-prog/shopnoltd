from pydantic import BaseModel
class RegisterIn(BaseModel):
    subdomain: str
    target: str
    record_type: str = "CNAME"
