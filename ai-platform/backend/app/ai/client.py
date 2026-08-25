"""
Model registry + thin call wrapper. Uses litellm so the rest of the codebase
never needs provider-specific SDKs — one function call works across every
provider below, and litellm normalizes every response (including tool calls)
into the same OpenAI-style shape.
"""

import litellm
from app.config import settings

# Friendly name -> (litellm model string, which settings field must be set)
# Order here also doubles as auto-selection priority (first configured wins).
MODEL_REGISTRY = {
    "claude-sonnet": ("anthropic/claude-sonnet-4-6", "ANTHROPIC_API_KEY"),
    "gpt-4o": ("openai/gpt-4o", "OPENAI_API_KEY"),
    "gemini-flash": ("gemini/gemini-2.0-flash", "GEMINI_API_KEY"),
    "grok": ("xai/grok-4.6", "XAI_API_KEY"),
    "mistral-large": ("mistral/mistral-large-latest", "MISTRAL_API_KEY"),
    "llama-groq": ("groq/llama-3.3-70b-versatile", "GROQ_API_KEY"),
    "deepseek-chat": ("deepseek/deepseek-chat", "DEEPSEEK_API_KEY"),
    "cohere-command": ("cohere/command-r-plus", "COHERE_API_KEY"),
}

DEFAULT_MODEL = "claude-sonnet"
AUTO = "auto"


def available_models() -> list[str]:
    """Only return models whose provider key is actually configured."""
    return [
        name
        for name, (_, key_field) in MODEL_REGISTRY.items()
        if getattr(settings, key_field, "")
    ]


def resolve_model(requested: str | None) -> str:
    """
    Manual selection: caller passed a specific, configured model name — use it.
    Auto selection: caller passed None, "auto", or an unconfigured/unknown
    name — fall back to the first configured model in MODEL_REGISTRY's
    priority order. Raises only if NOTHING is configured at all.
    """
    configured = available_models()
    if not configured:
        raise ValueError(
            "No model provider is configured — set at least one API key "
            "(e.g. ANTHROPIC_API_KEY) in the ai-platform-secret."
        )

    if requested and requested != AUTO and requested in configured:
        return requested

    return configured[0]


def call_model(model_name: str, **kwargs):
    litellm_model, key_field = MODEL_REGISTRY[model_name]
    api_key = getattr(settings, key_field, "")
    return litellm.completion(model=litellm_model, api_key=api_key, **kwargs)
