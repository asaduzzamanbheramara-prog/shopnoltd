"""
app/services/model_router.py

Central model resolution and provider execution.

Explicit model selections are deterministic: failures are returned to the API
instead of silently switching to an unrelated model. Automatic fallback remains
available only when the caller did not explicitly select a model.
"""

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decrypt_secret
from app.db.models import AIModel, AIProvider, ProviderType
from app.services.adapters.anthropic_adapter import AnthropicAdapter
from app.services.adapters.base import BaseAdapter, InferenceResult
from app.services.adapters.google_adapter import GoogleAdapter
from app.services.adapters.ollama_adapter import OllamaAdapter
from app.services.adapters.openai_adapter import OpenAIAdapter

ADAPTER_MAP: dict[ProviderType, type[BaseAdapter]] = {
    ProviderType.openai: OpenAIAdapter,
    ProviderType.anthropic: AnthropicAdapter,
    ProviderType.ollama: OllamaAdapter,
    ProviderType.google: GoogleAdapter,
    ProviderType.azure_openai: OpenAIAdapter,
    ProviderType.custom: OpenAIAdapter,
}


class ModelNotAvailableError(Exception):
    pass


class ProviderInferenceError(ModelNotAvailableError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


async def _resolve_model(
    db: AsyncSession,
    model_name: str | None,
    model_id,
) -> tuple[AIModel, AIProvider]:
    if model_id is not None:
        stmt = (
            select(AIModel)
            .join(AIProvider)
            .where(
                AIModel.id == model_id,
                AIModel.is_active,
                AIProvider.is_active,
            )
        )
    elif model_name:
        stmt = (
            select(AIModel)
            .join(AIProvider)
            .where(
                AIModel.model_name == model_name,
                AIModel.is_active,
                AIProvider.is_active,
            )
        )
    else:
        stmt = (
            select(AIModel)
            .join(AIProvider)
            .where(
                AIModel.is_active,
                AIProvider.is_active,
                AIModel.is_default,
            )
            .order_by(AIModel.priority.asc())
        )

    result = await db.execute(stmt)
    model = result.scalars().first()

    if model is None and model_id is not None:
        raise ModelNotAvailableError(f"AI model '{model_id}' is not active or does not exist.")

    if model is None and model_name is not None:
        raise ModelNotAvailableError(f"AI model '{model_name}' is not active or does not exist.")

    if model is None:
        stmt = (
            select(AIModel)
            .join(AIProvider)
            .where(AIModel.is_active, AIProvider.is_active)
            .order_by(AIModel.priority.asc())
        )
        result = await db.execute(stmt)
        model = result.scalars().first()

    if model is None:
        raise ModelNotAvailableError(
            "No active AI model is configured. Add a provider and activate at least one model "
            "via POST /api/ai/providers and /api/ai/models."
        )

    provider_result = await db.execute(
        select(AIProvider).where(AIProvider.id == model.provider_id)
    )
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
        api_key=api_key,
        base_url=provider.base_url,
        extra_config=provider.extra_config or {},
    )


def _requires_vision(attachments: list[dict] | None) -> bool:
    return any(
        str(item.get("mime_type") or "").lower().startswith("image/")
        and bool(item.get("data"))
        for item in attachments or []
    )


def _supports_vision(model: AIModel) -> bool:
    capabilities = model.capabilities or {}
    return bool(capabilities.get("supports_vision") or capabilities.get("vision"))


def _provider_error(model: AIModel, provider: AIProvider, exc: Exception) -> ProviderInferenceError:
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        status_code = response.status_code
        detail = ""
        try:
            payload = response.json()
            error = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(error, dict):
                detail = str(error.get("message") or error.get("code") or "")
            elif error:
                detail = str(error)
        except Exception:
            detail = ""

        if status_code == 402:
            message = (
                f"Provider '{provider.name}' rejected model '{model.model_name}' with HTTP 402 "
                "Payment Required. Check the provider account credits, billing state, "
                "or key spending limits."
            )
        else:
            message = (
                f"Provider '{provider.name}' rejected model '{model.model_name}' "
                f"with HTTP {status_code}."
            )
        if detail:
            message = f"{message} {detail}"
        return ProviderInferenceError(message, status_code)

    return ProviderInferenceError(
        f"Provider '{provider.name}' failed model '{model.model_name}': {exc}",
        502,
    )


async def _generate(
    model: AIModel,
    provider: AIProvider,
    adapter: BaseAdapter,
    prompt: str,
    attachments: list[dict],
) -> InferenceResult:
    try:
        return await adapter.generate(
            model.model_name,
            prompt,
            timeout=settings.inference_timeout_seconds,
            attachments=attachments,
        )
    except Exception as exc:
        raise _provider_error(model, provider, exc) from exc


async def run_inference(
    db: AsyncSession,
    prompt: str,
    model_name: str | None = None,
    model_id=None,
    attachments: list[dict] | None = None,
) -> tuple[InferenceResult, AIModel]:
    attachments = attachments or []
    needs_vision = _requires_vision(attachments)
    explicit_selection = model_id is not None or bool(model_name)

    model, provider = await _resolve_model(db, model_name, model_id)

    if needs_vision and not _supports_vision(model):
        raise ModelNotAvailableError(
            f"Model '{model.model_name}' is not marked as vision-capable. "
            "Enable capabilities.supports_vision for a compatible model."
        )

    adapter = _build_adapter(provider)

    try:
        result = await _generate(model, provider, adapter, prompt, attachments)
        return result, model
    except ProviderInferenceError as first_error:
        if explicit_selection:
            raise

        fallback_stmt = (
            select(AIModel)
            .join(AIProvider)
            .where(
                AIModel.is_active,
                AIProvider.is_active,
                AIModel.id != model.id,
            )
        )
        if needs_vision:
            fallback_stmt = fallback_stmt.where(
                AIModel.capabilities["supports_vision"].as_boolean().is_(True)
            )

        fallback_stmt = fallback_stmt.order_by(AIModel.priority.asc())
        result = await db.execute(fallback_stmt)
        fallback_model = result.scalars().first()

        if fallback_model is None:
            raise ModelNotAvailableError(
                f"Default model '{model.model_name}' failed: {first_error}"
            ) from first_error

        provider_result = await db.execute(
            select(AIProvider).where(AIProvider.id == fallback_model.provider_id)
        )
        fallback_provider = provider_result.scalar_one()
        fallback_adapter = _build_adapter(fallback_provider)

        try:
            result = await _generate(
                fallback_model,
                fallback_provider,
                fallback_adapter,
                prompt,
                attachments,
            )
            return result, fallback_model
        except ProviderInferenceError as fallback_error:
            raise ModelNotAvailableError(
                f"Default model '{model.model_name}' failed: {first_error}; "
                f"fallback '{fallback_model.model_name}' failed: {fallback_error}"
            ) from fallback_error
