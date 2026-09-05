from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "shopnoltd-oauth-service"
    env: str = "production"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.shopno-data.svc.cluster.local:5432/oauth"
    )
    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_url: str = "https://auth.shopnoltd.dpdns.org"
    keycloak_admin_user: str = "admin"
    keycloak_admin_password: str = "CHANGE_ME"
    keycloak_realm: str = "shopnoltd"
    keycloak_audience: str = "oauth-service"

    @property
    def cors_origins_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cors_origin_regex(self) -> str:
        # allow_origins does exact string matching in Starlette's CORSMiddleware,
        # so a literal "*" embedded in a domain string (e.g. "https://*.shopnoltd.dpdns.org")
        # never actually matches any real browser Origin header. This regex matches
        # the bare root domain and any subdomain instead.
        return r"^https://([a-z0-9-]+\.)*shopnoltd\.dpdns\.org$"


settings = Settings()
