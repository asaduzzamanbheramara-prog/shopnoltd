from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-meet-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/meet"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    jitsi_jwt_app_id: str = "shopnoltd"
    jitsi_jwt_secret: str = "CHANGE_ME_JITSI_JWT"
    jitsi_url: str = "https://meet.shopnoltd.dpdns.org"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "meet-service"
settings = Settings()
