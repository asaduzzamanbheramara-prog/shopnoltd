from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = "production"
    app_name: str = "shopnoltd-storage-service"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.shopno-data.svc.cluster.local:5432/storage"
    )
    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    minio_endpoint: str = "minio.data.svc.cluster.local:9000"
    minio_access_key: str = "shopno"
    minio_secret_key: str = "CHANGE_ME"
    minio_secure: bool = False
    keycloak_audience: str = "storage-service"

    @property
    def cors_origins_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cors_origin_regex(self) -> str:
        # allow_origins does exact string matching in Starlette's CORSMiddleware,
        # so a literal "*" embedded in a domain string (e.g. "https://*.shopnoltd.dpdns.org")
        # never actually matches any real browser Origin header. This regex matches
        # the bare root domain and any subdomain instead.
        return r"^https://([a-z0-9-]+\.)*shopnoltd\.dpdns\.org$"


settings = Settings()
