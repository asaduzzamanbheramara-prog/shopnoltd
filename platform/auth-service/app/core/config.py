from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = "production"
    app_name: str = "shopnoltd-auth-service"

    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.shopno-data.svc.cluster.local:5432/auth"
    )

    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/0"

    cors_origins: str = "https://*.shopnoltd.dpdns.org"

    # Keycloak base URL. Do NOT include /realms/<realm> here.
    keycloak_url: str = "https://auth.shopnoltd.dpdns.org"

    keycloak_realm: str = "shopnoltd"

    # Full Keycloak issuer URL used for JWKS/token verification.
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"

    keycloak_audience: str = "auth-service"

    keycloak_web_client_id: str = "shopnoltd-web"

    keycloak_admin_client_id: str = ""
    keycloak_admin_client_secret: str = ""

    signup_verify_email: bool = True

    public_base_url: str = "https://auth-service.shopnoltd.dpdns.org"

    @property
    def cors_origins_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
