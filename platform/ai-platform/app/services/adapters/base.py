from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class InferenceResult:
    text: str
    tokens_used: int
    raw: dict


class BaseAdapter(ABC):
    """Every provider adapter implements this same shape so model_router
    can call any of them interchangeably."""

    def __init__(self, api_key: str | None, base_url: str | None, extra_config: dict):
        self.api_key = api_key
        self.base_url = base_url
        self.extra_config = extra_config or {}

    def require_api_key(self, provider_label: str) -> str:
        """Fail locally and safely when a credential-backed provider has no key."""
        if not self.api_key or not self.api_key.strip():
            raise RuntimeError(f"{provider_label} provider has no API key configured")
        return self.api_key

    @abstractmethod
    async def generate(self, model_name: str, prompt: str, timeout: int) -> InferenceResult: ...

    @abstractmethod
    async def health_check(self, timeout: int = 5) -> bool:
        """Cheap connectivity check — used by the /providers/{id}/test endpoint."""
        ...
