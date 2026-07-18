from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "shopnoltd-event-service"
    env: str = "production"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/events"
    )
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "event-service"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
