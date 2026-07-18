from pydantic import BaseModel


class TenantRouteIn(BaseModel):
    subdomain: str
    tenant_id: str
    plan: str = "free"
    storage_quota_gb: int = 10
    user_quota: int = 10


class TenantRouteOut(BaseModel):
    subdomain: str
    tenant_id: str
    namespace: str
    plan: str
    storage_quota_gb: int
    user_quota: int
    active: bool
