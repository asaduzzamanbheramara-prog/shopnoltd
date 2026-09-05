from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = "production"
    app_name: str = "shopnoltd-freedomain-service"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.shopno-data.svc.cluster.local:5432/freedomain"
    )
    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/0"
    cors_origins: str = "https://shopnoltd.dpdns.org"
    domain_service_url: str = "http://domain-service.shopno-platform.svc.cluster.local:8080"
    parent_zone: str = "shopnoltd.dpdns.org"
    keycloak_audience: str = "freedomain-service"
    keycloak_issuer: str = "http://keycloak.shopno-identity.svc.cluster.local/realms/shopnoltd"

    @property
    def cors_origins_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cors_origin_regex(self) -> str:
        # Previously only matched the bare root domain exactly, missing every
        # subdomain (including this service's own freedomain./domain. hosts).
        # This regex matches the root domain and any subdomain instead.
        return r"^https://([a-z0-9-]+\.)*shopnoltd\.dpdns\.org$"


settings = Settings()
