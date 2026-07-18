"""Configuration loaded from env."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "shopnoltd-payment-service"
    env: str = "production"
    version: str = "0.1.0"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/payments"
    )
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "payment-service"
    jwt_audience: str = "shopnoltd"
    exchange_service_url: str = "http://exchange-service.shopno-payments.svc.cluster.local:8080"
    billing_engine_url: str = "http://billing-engine.shopno-payments.svc.cluster.local:8080"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    paypal_client_id: str = ""
    paypal_secret: str = ""
    binance_pay_key: str = ""
    binance_pay_secret: str = ""
    payeer_account: str = ""
    payeer_api_key: str = ""
    bkash_app_key: str = ""
    bkash_app_secret: str = ""
    nagad_merchant_id: str = ""
    nagad_merchant_key: str = ""
    nagad_merchant_private_key: str = ""
    nagad_pg_public_key: str = ""
    nagad_sandbox: bool = True
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    sslcommerz_store_id: str = ""
    sslcommerz_store_password: str = ""
    sslcommerz_sandbox: bool = True
    base_callback_url: str = "https://api.shopnoltd.dpdns.org"
    rocket_merchant_id: str = ""
    rocket_merchant_key: str = ""
    admin_approval_required: bool = True
    min_deposit: float = 1.0
    max_deposit: float = 100000.0
    min_withdrawal: float = 5.0
    max_withdrawal: float = 50000.0
    platform_fee_pct: float = 1.5

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
