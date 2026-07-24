from pydantic_settings import BaseSettings


class Settings(BaseSettings):
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


settings = Settings()
