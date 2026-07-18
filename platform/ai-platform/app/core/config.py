from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "shopnoltd-ai-platform"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/ai"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model: str = "microsoft/Phi-3-mini-4k-instruct"
    llm_url: str = "http://localhost:11434"  # Ollama default
    storage_service_url: str = "http://storage-service.shopno-platform.svc.cluster.local:8080"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "ai-platform"


settings = Settings()
