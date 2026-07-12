from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-search-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/search"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    opensearch_url: str = "https://opensearch.shopno-data.svc.cluster.local:9200"
    opensearch_user: str = "admin"
    opensearch_password: str = "CHANGE_ME"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "search-service"
settings = Settings()
