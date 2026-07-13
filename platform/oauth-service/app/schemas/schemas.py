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
class CustomerIn(BaseModel):
    email: str; name: str = ""; phone: str = ""
    billing_address: dict = {}
    preferences: dict = {}
class CustomerOut(BaseModel):
    id: str; tenant_id: str; email: str; name: str; phone: str
    billing_address: dict; preferences: dict; active: bool
    class Config: from_attributes = True
class TenantSettingsPatch(BaseModel):
    """Partial update -- only the keys present are merged into Tenant.settings.
    theme: colors/logo/fonts. texts: editable UI copy by key. plugins: which
    optional modules are enabled for this tenant."""
    theme: Optional[dict] = None
    texts: Optional[dict] = None
    plugins: Optional[dict] = None
class TenantSettingsOut(BaseModel):
    tenant_id: str
    theme: dict = {}
    texts: dict = {}
    plugins: dict = {}
