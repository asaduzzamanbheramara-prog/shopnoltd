"""Live model catalog discovery and reconciliation for configured AI providers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AIModel, AIProvider
from app.services.model_router import _build_adapter


def _display_name(model: dict[str, Any]) -> str:
    return str(model.get("display_name") or model.get("name") or model.get("id") or "Unknown model")


def _model_id(model: dict[str, Any]) -> str | None:
    value = model.get("id") or model.get("name")
    if not value:
        return None
    value = str(value)
    if value.startswith("models/"):
        value = value[7:]
    return value


def _recommended(model: dict[str, Any]) -> bool:
    value = model.get("recommended")
    if isinstance(value, bool):
        return value
    name = (_model_id(model) or "").lower()
    return any(token in name for token in ("sonnet", "opus", "gpt-5", "gpt-4", "gemini-2.5", "gemini-2.0", "llama-4", "qwen3", "deepseek-v3"))


def _safe_provider_error(exc: Exception) -> dict[str, Any]:
    """Return actionable provider diagnostics without leaking request URLs or credentials."""
    detail: dict[str, Any] = {"error_type": type(exc).__name__}
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        detail["http_status"] = response.status_code
        try:
            payload = response.json()
        except (ValueError, TypeError):
            payload = {}
        provider_error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(provider_error, dict):
            if provider_error.get("code") is not None:
                detail["provider_error_code"] = provider_error["code"]
            if provider_error.get("status"):
                detail["provider_error_status"] = str(provider_error["status"])[:80]
            if provider_error.get("message"):
                # Google/provider error messages are useful for diagnosis; never include
                # the exception string because it can contain a URL with a query key.
                detail["provider_error_message"] = str(provider_error["message"])[:300]
    elif isinstance(exc, httpx.TimeoutException):
        detail["provider_error_message"] = "Provider request timed out."
    elif isinstance(exc, httpx.RequestError):
        detail["provider_error_message"] = "Provider network request failed."
    return detail


async def sync_provider_models(
    db: AsyncSession,
    provider: AIProvider,
    *,
    activation: str = "recommended",
) -> dict[str, Any]:
    """Discover models without deleting the last-known-good catalog."""
    adapter = _build_adapter(provider)
    discovered = await adapter.list_models()
    if discovered is None:
        return {
            "provider": provider.name,
            "status": "unsupported",
            "discovered": 0,
            "created": 0,
            "updated": 0,
        }

    now = datetime.now(timezone.utc).isoformat()
    created = updated = 0
    discovered_ids: set[str] = set()

    for raw in discovered:
        model_name = _model_id(raw)
        if not model_name:
            continue
        discovered_ids.add(model_name)
        result = await db.execute(
            select(AIModel).where(
                AIModel.provider_id == provider.id,
                AIModel.model_name == model_name,
            )
        )
        model = result.scalar_one_or_none()
        existing_capabilities = dict(model.capabilities or {}) if model else {}
        remote_capabilities = dict(raw.get("capabilities") or {})
        capabilities = {**existing_capabilities, **remote_capabilities}
        capabilities["catalog"] = {
            **dict(capabilities.get("catalog") or {}),
            "last_seen": now,
            "source": provider.provider_type.value,
        }
        if raw.get("context_window") is not None:
            capabilities["context_window"] = raw["context_window"]
        if raw.get("input_token_limit") is not None:
            capabilities["input_token_limit"] = raw["input_token_limit"]
        if raw.get("output_token_limit") is not None:
            capabilities["output_token_limit"] = raw["output_token_limit"]
        if raw.get("pricing") is not None:
            capabilities["pricing"] = raw["pricing"]

        if model is None:
            model = AIModel(
                provider_id=provider.id,
                model_name=model_name,
                display_name=_display_name(raw),
                is_active=activation == "all" or (activation == "recommended" and _recommended(raw)),
                is_default=False,
                capabilities=capabilities,
                priority=100,
            )
            db.add(model)
            created += 1
        else:
            model.display_name = _display_name(raw) or model.display_name
            model.capabilities = capabilities
            if activation == "all":
                model.is_active = True
            elif activation == "none":
                pass
            elif activation == "recommended" and _recommended(raw):
                model.is_active = True
            updated += 1

    await db.flush()
    return {
        "provider": provider.name,
        "status": "connected",
        "discovered": len(discovered_ids),
        "created": created,
        "updated": updated,
    }


async def sync_all_providers(
    db: AsyncSession,
    *,
    activation: str = "recommended",
) -> list[dict[str, Any]]:
    if activation not in {"recommended", "all", "none"}:
        raise ValueError("activation must be one of: recommended, all, none")

    result = await db.execute(
        select(AIProvider).where(AIProvider.is_active).order_by(AIProvider.name)
    )
    reports: list[dict[str, Any]] = []
    for provider in result.scalars().all():
        try:
            reports.append(
                await sync_provider_models(db, provider, activation=activation)
            )
        except Exception as exc:
            # A provider outage must never erase its existing model catalog.
            # Keep diagnostics actionable while excluding request URLs/API keys.
            reports.append({
                "provider": provider.name,
                "status": "error",
                "discovered": 0,
                "created": 0,
                "updated": 0,
                "diagnostic": _safe_provider_error(exc),
            })
    await db.commit()
    return reports
