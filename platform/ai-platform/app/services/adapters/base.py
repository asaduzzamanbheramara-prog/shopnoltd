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

    @abstractmethod
    async def generate(self, model_name: str, prompt: str, timeout: int) -> InferenceResult: ...

    @abstractmethod
    async def health_check(self, timeout: int = 5) -> bool:
        """Cheap connectivity check — used by the /providers/{id}/test endpoint."""
        ...
