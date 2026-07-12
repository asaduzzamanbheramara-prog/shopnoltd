from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-domain-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/domains"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    powerdns_api: str = "http://powerdns.shopno-apps.svc.cluster.local:8081/api/v1"
    powerdns_key: str = "CHANGE_ME_POWERDNS_KEY"
    keycloak_audience: str = "domain-service"
    @property
    def cors_origins_list(self): return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
settings = Settings()
