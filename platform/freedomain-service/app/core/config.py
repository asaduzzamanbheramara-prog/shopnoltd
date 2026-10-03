from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = "production"
    app_name: str = "shopnoltd-freedomain-service"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.shopno-data.svc.cluster.local:5432/freedomain"
    )
    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/0"
    cors_origins: str = "https://shopnoltd.dpdns.org"
    domain_service_url: str = "http://domain-service.shopno-platform.svc.cluster.local:8080"
    freedomain_internal_key: str = ""
    parent_zone: str = "shopnoltd.dpdns.org"
    default_target: str = "shopnoltd.dpdns.org"
    default_record_type: str = "CNAME"
    wildcard_dns_fallback: bool = False
    keycloak_jwks_url: str | None = None
    keycloak_audience: str = "api-service"
    keycloak_issuer: str = "http://keycloak.shopno-identity.svc.cluster.local/realms/shopnoltd"

    @property
    def cors_origins_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cors_origin_regex(self) -> str:
        return r"^https://([a-z0-9-]+\.)*shopnoltd\.dpdns\.org$"


settings = Settings()
