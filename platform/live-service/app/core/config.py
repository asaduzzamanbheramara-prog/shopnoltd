from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "shopnoltd-live-service"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.shopno-data.svc.cluster.local:5432/live"
    )
    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    owncast_admin_url: str = "https://live.shopnoltd.dpdns.org"
    owncast_api_key: str = "CHANGE_ME_OWNCAST_KEY"
    storage_service_url: str = "http://storage-service.shopno-platform.svc.cluster.local:8080"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "live-service"


settings = Settings()
