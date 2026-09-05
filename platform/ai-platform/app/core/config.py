from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    env: str = "production"
    app_name: str = "shopnoltd-ai-platform"

    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.shopno-data.svc.cluster.local:5432/ai"
    )

    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/0"

    cors_origins: str = "https://*.shopnoltd.dpdns.org"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    llm_model: str = "microsoft/Phi-3-mini-4k-instruct"

    llm_url: str = "http://ollama.shopno-apps.svc.cluster.local:11434"

    inference_timeout_seconds: int = 120

    ai_key_encryption_key: str | None = None

    storage_service_url: str = "http://storage-service.shopno-platform.svc.cluster.local:8080"

    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"

    keycloak_audience: str = "ai-platform"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cors_origin_regex(self) -> str:
        # allow_origins does exact string matching in Starlette's CORSMiddleware,
        # so a literal "*" embedded in a domain string (e.g. "https://*.shopnoltd.dpdns.org")
        # never actually matches any real browser Origin header. This regex matches
        # the bare root domain and any subdomain instead.
        return r"^https://([a-z0-9-]+\.)*shopnoltd\.dpdns\.org$"


settings = Settings()
