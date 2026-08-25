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

    # Model provider keys — add whichever you actually have. Leave blank to
    # disable that provider (the model registry in ai/client.py skips models
    # whose provider key is empty).
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    XAI_API_KEY: str = ""
    COHERE_API_KEY: str = ""


settings = Settings()
