from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "shopnoltd-notification-service"
    env: str = "production"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/notifications"
    )
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/3"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "notification-service"
    smtp_host: str = "mailcow.shopno-apps.svc.cluster.local"
    smtp_port: int = 587
    smtp_user: str = "noreply@shopnoltd.dpdns.org"
    smtp_password: str = ""
    smtp_from: str = "Shopnoltd <noreply@shopnoltd.dpdns.org>"
    fcm_server_key: str = ""
    twilio_sid: str = ""
    twilio_token: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
