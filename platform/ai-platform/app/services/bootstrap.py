"""Idempotent bootstrap for production AI providers/models.

Provider credentials are supplied only through Kubernetes secrets/environment
variables. No credential is persisted in source control.
"""

from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_secret
from app.db.models import AIModel, AIProvider, ProviderType


PROVIDERS = (
    {
        "env_key": "GOOGLE_AI_API_KEY",
        "name": "Google Gemini",
        "provider_type": ProviderType.google,
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "model_env": "GOOGLE_AI_MODEL",
        "default_model": "gemini-2.5-flash",
        "display_name": "Gemini Flash",
        "priority": 10,
    },
    {
        "env_key": "GROQ_API_KEY",
        "name": "Groq",
        "provider_type": ProviderType.custom,
        "base_url": "https://api.groq.com/openai/v1",
        "model_env": "GROQ_AI_MODEL",
        "default_model": "llama-3.3-70b-versatile",
        "display_name": "Groq Llama 3.3 70B",
        "priority": 20,
    },
    {
        "env_key": "OPENROUTER_API_KEY",
        "name": "OpenRouter",
        "provider_type": ProviderType.custom,
        "base_url": "https://openrouter.ai/api/v1",
        "model_env": "OPENROUTER_AI_MODEL",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
        "display_name": "OpenRouter Llama 3.3 70B Free",
        "priority": 30,
    },
    {
        "env_key": "CEREBRAS_API_KEY",
        "name": "Cerebras",
        "provider_type": ProviderType.custom,
        "base_url": "https://api.cerebras.ai/v1",
        "model_env": "CEREBRAS_AI_MODEL",
        "default_model": "llama-3.3-70b",
        "display_name": "Cerebras Llama 3.3 70B",
        "priority": 40,
    },
)


async def bootstrap_providers(db: AsyncSession) -> int:
    """Create/update configured providers and models; skip absent credentials."""
    configured = 0

    for spec in PROVIDERS:
        api_key = os.getenv(spec["env_key"], "").strip()
        if not api_key:
            continue

        result = await db.execute(select(AIProvider).where(AIProvider.name == spec["name"]))
        provider = result.scalar_one_or_none()
        if provider is None:
            provider = AIProvider(
                name=spec["name"],
                provider_type=spec["provider_type"],
                api_key_encrypted=encrypt_secret(api_key),
                base_url=spec["base_url"],
                is_active=True,
                extra_config={},
            )
            db.add(provider)
            await db.flush()
        else:
            provider.provider_type = spec["provider_type"]
            provider.base_url = spec["base_url"]
            provider.is_active = True
            if not provider.api_key_encrypted:
                provider.api_key_encrypted = encrypt_secret(api_key)

        model_name = os.getenv(spec["model_env"], spec["default_model"]).strip()
        model_result = await db.execute(
            select(AIModel).where(
                AIModel.provider_id == provider.id,
                AIModel.model_name == model_name,
            )
        )
        model = model_result.scalar_one_or_none()
        if model is None:
            model = AIModel(
                provider_id=provider.id,
                model_name=model_name,
                display_name=spec["display_name"],
                is_active=True,
                is_default=(configured == 0),
                priority=spec["priority"],
                capabilities={"chat": True},
            )
            db.add(model)
        else:
            model.is_active = True
            model.priority = spec["priority"]
            if configured == 0:
                model.is_default = True

        configured += 1

    if configured:
        await db.commit()

    return configured
