"""
Model registry + thin call wrapper. Uses litellm so the rest of the codebase
never needs provider-specific SDKs — one function call works for Claude,
GPT, or Gemini, and litellm normalizes every response (including tool calls)
into the same OpenAI-style shape.
"""

import litellm
from app.config import settings

# Friendly name -> (litellm model string, which settings field must be set)
MODEL_REGISTRY = {
    "claude-sonnet": ("anthropic/claude-sonnet-4-6", "ANTHROPIC_API_KEY"),
    "gpt-4o": ("openai/gpt-4o", "OPENAI_API_KEY"),
    "gemini-flash": ("gemini/gemini-2.0-flash", "GEMINI_API_KEY"),
}

DEFAULT_MODEL = "claude-sonnet"


def available_models() -> list[str]:
    """Only return models whose provider key is actually configured."""
    return [
        name
        for name, (_, key_field) in MODEL_REGISTRY.items()
        if getattr(settings, key_field, "")
    ]


def call_model(model_name: str, **kwargs):
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model: {model_name}")

    litellm_model, key_field = MODEL_REGISTRY[model_name]
    api_key = getattr(settings, key_field, "")
    if not api_key:
        raise ValueError(f"{model_name} is not configured (missing {key_field})")

    return litellm.completion(model=litellm_model, api_key=api_key, **kwargs)
