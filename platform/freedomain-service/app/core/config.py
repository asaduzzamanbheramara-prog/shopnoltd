from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "shopnoltd-freedomain-service"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/freedomain"
    )
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    domain_service_url: str = "http://domain-service.shopno-platform.svc.cluster.local:8080"
    parent_zone: str = "freedomain.shopnoltd.dpdns.org"
    keycloak_audience: str = "freedomain-service"

    @property
    def cors_origins_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
