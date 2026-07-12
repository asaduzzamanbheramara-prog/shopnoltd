from pydantic import BaseModel
from typing import Optional
class UserIn(BaseModel):
    email: str; name: str = ""; password: str = ""; tenant_id: Optional[str] = None
class UserOut(BaseModel):
    id: str; email: str; name: str; tenant_id: Optional[str]; roles: list
    class Config: from_attributes = True
class TenantIn(BaseModel):
    name: str; subdomain: str; plan: str = "free"
class TenantOut(BaseModel):
    id: str; name: str; subdomain: str; plan: str
    class Config: from_attributes = True
