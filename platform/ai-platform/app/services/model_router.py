"""
app/services/model_router.py

Central place that:
  1. Looks up the active model (either by name, or the default/highest-priority
     active model if none specified).
  2. Builds the right adapter for that model's provider.
  3. Calls it, with one retry on failure and a clear error if nothing is
     configured (rather than silently falling back to the old stub).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decrypt_secret
from app.db.models import AIModel, AIProvider, ProviderType
from app.services.adapters.anthropic_adapter import AnthropicAdapter
from app.services.adapters.base import BaseAdapter, InferenceResult
from app.services.adapters.ollama_adapter import OllamaAdapter
from app.services.adapters.openai_adapter import OpenAIAdapter

ADAPTER_MAP: dict[ProviderType, type[BaseAdapter]] = {
    ProviderType.openai: OpenAIAdapter,
    ProviderType.anthropic: AnthropicAdapter,
    ProviderType.ollama: OllamaAdapter,
    ProviderType.azure_openai: OpenAIAdapter,  # Azure OpenAI is wire-compatible enough for chat/completions
    ProviderType.custom: OpenAIAdapter,  # any OpenAI-compatible server (vLLM, LM Studio, etc.)
    # ProviderType.google: add a GoogleAdapter here when needed
}


class ModelNotAvailableError(Exception):
    pass


async def _resolve_model(db: AsyncSession, model_name: str | None) -> tuple[AIModel, AIProvider]:
    if model_name:
        stmt = (
            select(AIModel)
            .join(AIProvider)
            .where(
                AIModel.model_name == model_name,
                AIModel.is_active,
                AIProvider.is_active,
            )  # noqa: E712
        )
    else:
        stmt = (
            select(AIModel)
            .join(AIProvider)
            .where(AIModel.is_active, AIProvider.is_active, AIModel.is_default)  # noqa: E712
            .order_by(AIModel.priority.asc())
        )
    result = await db.execute(stmt)
    model = result.scalars().first()

    if model is None and model_name is None:
        # No explicit default set — fall back to any active model, lowest priority number first.
        stmt = (
            select(AIModel)
            .join(AIProvider)
            .where(AIModel.is_active, AIProvider.is_active)  # noqa: E712
            .order_by(AIModel.priority.asc())
        )
        result = await db.execute(stmt)
        model = result.scalars().first()

    if model is None:
        raise ModelNotAvailableError(
            "No active AI model is configured. Add a provider and activate at least one model "
            "via POST /api/ai/providers and /api/ai/models."
        )

    provider_result = await db.execute(select(AIProvider).where(AIProvider.id == model.provider_id))
    provider = provider_result.scalar_one()
    return model, provider


def _build_adapter(provider: AIProvider) -> BaseAdapter:
    adapter_cls = ADAPTER_MAP.get(provider.provider_type)
    if adapter_cls is None:
        raise ModelNotAvailableError(
            f"No adapter implemented for provider type '{provider.provider_type}'."
        )
    api_key = decrypt_secret(provider.api_key_encrypted) if provider.api_key_encrypted else None
    return adapter_cls(
        api_key=api_key, base_url=provider.base_url, extra_config=provider.extra_config or {}
    )


async def run_inference(
    db: AsyncSession, prompt: str, model_name: str | None = None
) -> InferenceResult:
    model, provider = await _resolve_model(db, model_name)
    adapter = _build_adapter(provider)
    try:
        return await adapter.generate(
            model.model_name, prompt, timeout=settings.inference_timeout_seconds
        )
    except Exception as exc:
        # One fallback attempt to the next-highest-priority active model, if one exists
        # and it's different from the one that just failed.
        fallback_stmt = (
            select(AIModel)
            .join(AIProvider)
            .where(AIModel.is_active, AIProvider.is_active, AIModel.id != model.id)  # noqa: E712
            .order_by(AIModel.priority.asc())
        )
        result = await db.execute(fallback_stmt)
        fallback_model = result.scalars().first()
        if fallback_model is None:
            raise ModelNotAvailableError(
                f"Inference failed on '{model.model_name}' and no fallback model is available: {exc}"
            ) from exc

        provider_result = await db.execute(
            select(AIProvider).where(AIProvider.id == fallback_model.provider_id)
        )
        fallback_provider = provider_result.scalar_one()
        fallback_adapter = _build_adapter(fallback_provider)
        return await fallback_adapter.generate(
            fallback_model.model_name, prompt, timeout=settings.inference_timeout_seconds
        )
