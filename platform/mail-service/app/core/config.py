from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "shopnoltd-mail-service"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.shopno-data.svc.cluster.local:5432/mail"
    )
    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    mailcow_api_url: str = "https://mail.shopnoltd.dpdns.org/api/v1"
    mailcow_api_key: str = "CHANGE_ME_MAILCOW_KEY"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "mail-service"

    @property
    def cors_origins_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
