from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-oauth-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/oauth"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_url: str = "https://auth.shopnoltd.dpdns.org"
    keycloak_admin_user: str = "admin"
    keycloak_admin_password: str = "CHANGE_ME"
    keycloak_realm: str = "shopnoltd"
    keycloak_audience: str = "oauth-service"
    @property
    def cors_origins_list(self): return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
settings = Settings()
