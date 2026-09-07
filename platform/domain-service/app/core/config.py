from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = "production"
    app_name: str = "shopnoltd-domain-service"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.shopno-data.svc.cluster.local:5432/domains"
    )
    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/0"
    cors_origins: str = "https://shopnoltd.dpdns.org"
    powerdns_api: str = "http://powerdns.shopno-apps.svc.cluster.local:8081/api/v1"
    powerdns_key: str = "CHANGE_ME_POWERDNS_KEY"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "domain-service"

    # Server-to-server billing authorization. Keep this in a Kubernetes Secret.
    billing_engine_url: str = "http://billing-engine.shopno-payments.svc.cluster.local:5000"
    billing_internal_key: str = ""
    billing_currency: str = "USD"

    # Namecheap registrar configuration. API access must be enabled and the
    # caller IP must be whitelisted in Namecheap before production use.
    namecheap_api_key: str = ""
    namecheap_username: str = ""
    namecheap_client_ip: str = ""
    namecheap_sandbox: bool = True

    @property
    def cors_origins_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cors_origin_regex(self) -> str:
        return r"^https://([a-z0-9-]+\.)*shopnoltd\.dpdns\.org$"


settings = Settings()
