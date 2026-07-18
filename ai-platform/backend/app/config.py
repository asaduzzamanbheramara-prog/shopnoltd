"""
Central configuration for the Shopnoltd AI Platform backend.
Values are loaded from environment variables (see .env.example).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Shopnoltd AI Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://platform:platform@db:5432/platform"

    # Auth
    JWT_SECRET_KEY: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Anthropic API (used in Milestone 2 — AI engine)
    ANTHROPIC_API_KEY: str = ""


settings = Settings()
