from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)
    database_url: str
    redis_url: str = "redis://redis.shopno-data.svc.cluster.local:6379/0"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "api-service"
    keycloak_jwks_url: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd/protocol/openid-connect/certs"


settings = Settings()
