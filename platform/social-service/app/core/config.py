from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = "production"
    app_name: str = "shopnoltd-social-service"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.shopno-data.svc.cluster.local:5432/social"
    )
    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/4"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_jwks_url: str | None = None
    keycloak_audience: str = "api-service"
    storage_service_url: str = "http://storage-service.shopno-platform.svc.cluster.local:8080"
    # Provider OAuth configuration is injected from the runtime secret manager.
    # Never commit client secrets or user access/refresh tokens to Git.
    provider_oauth_encryption_key: str | None = None
    provider_oauth_state_secret: str | None = None
    provider_oauth_redirect_uri: str = "https://shopnoltd.dpdns.org/connections/oauth/callback"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    microsoft_client_id: str | None = None
    microsoft_client_secret: str | None = None
    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None
    x_client_id: str | None = None
    x_client_secret: str | None = None
    facebook_client_id: str | None = None
    facebook_client_secret: str | None = None
    instagram_client_id: str | None = None
    instagram_client_secret: str | None = None
    tiktok_client_key: str | None = None
    tiktok_client_secret: str | None = None
    telegram_bot_token: str | None = None
    whatsapp_client_id: str | None = None
    whatsapp_client_secret: str | None = None
    threecx_client_id: str | None = None
    threecx_client_secret: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cors_origin_regex(self) -> str:
        # allow_origins does exact string matching in Starlette's CORSMiddleware,
        # so a literal "*" embedded in a domain string (e.g. "https://*.shopnoltd.dpdns.org")
        # never actually matches any real browser Origin header. This regex matches
        # the bare root domain and any subdomain instead.
        return r"^https://([a-z0-9-]+\.)*shopnoltd\.dpdns\.org$"


settings = Settings()
