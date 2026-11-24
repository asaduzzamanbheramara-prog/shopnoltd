from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "shopnoltd-api-service"
    env: str = "production"
    database_url: str
    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/0"
    # Comma-separated exact origins for approved custom domains. Shopnoltd's own
    # apex/subdomains are covered by cors_origin_regex below.
    cors_origins: str = ""
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_jwks_url: str | None = None
    keycloak_audience: str = "api-service"

    @property
    def cors_origins_list(self) -> list[str]:
        # Never pass wildcard patterns to allow_origins: Starlette expects exact
        # origins here. Wildcard Shopnoltd hosts are handled by cors_origin_regex.
        return [o.strip() for o in self.cors_origins.split(",") if o.strip() and "*" not in o]

    @property
    def cors_origin_regex(self) -> str:
        # allow_origins does exact string matching in Starlette's CORSMiddleware,
        # so a literal "*" embedded in a domain string (e.g. "https://*.shopnoltd.dpdns.org")
        # never actually matches any real browser Origin header. This regex matches
        # the bare root domain and any subdomain instead.
        return r"^https://([a-z0-9-]+\.)*shopnoltd\.dpdns\.org$"


settings = Settings()
