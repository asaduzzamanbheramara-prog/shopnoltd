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
    # Use internal Kubernetes service DNS to avoid ingress/TLS issues.
    keycloak_url: str = "http://keycloak.shopno-identity.svc.cluster.local:8080"

    keycloak_realm: str = "shopnoltd"

    # Full Keycloak issuer URL used for JWKS/token verification.
    # Must match Keycloak's KEYCLOAK_FRONTEND_URL for token validation.
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

    @property
    def cors_origin_regex(self) -> str:
        # allow_origins does exact string matching in Starlette's CORSMiddleware,
        # so a literal "*" embedded in a domain string (e.g. "https://*.shopnoltd.dpdns.org")
        # never actually matches any real browser Origin header. This regex matches
        # the bare root domain and any subdomain instead.
        return r"^https://([a-z0-9-]+\.)*shopnoltd\.dpdns\.org$"


settings = Settings()
