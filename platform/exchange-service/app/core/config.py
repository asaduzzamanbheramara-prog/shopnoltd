from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "shopnoltd-exchange-service"
    env: str = "production"
    database_url: str = (
        "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/exchange"
    )
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/1"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    binance_api: str = "https://api.binance.com"
    coingecko_api: str = "https://api.coingecko.com/api/v3"
    openexchangerates_app_id: str = ""
    rate_refresh_seconds: int = 60
    supported_fiat: str = "USD,EUR,GBP,BDT,INR,PKR,MYR,NGN,ZAR"
    supported_crypto: str = "BTC,ETH,USDT,BNB,SOL,TRX,XRP,ADA,DOGE,USDC"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def fiat_list(self) -> list[str]:
        return [c.strip() for c in self.supported_fiat.split(",")]

    @property
    def crypto_list(self) -> list[str]:
        return [c.strip() for c in self.supported_crypto.split(",")]


settings = Settings()
