"""Base payment provider."""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    def __init__(self, name: str):
        self.name = name
        # Providers must explicitly opt in when their runtime configuration
        # supports the operation. This prevents unconfigured integrations from
        # being advertised as available by the checkout method registry.
        self.enabled = False

    @abstractmethod
    async def create_deposit(self, tx, **kwargs) -> dict: ...
    @abstractmethod
    async def create_withdrawal(self, tx, **kwargs) -> dict: ...
    @abstractmethod
    async def verify_webhook(self, request_body: bytes, headers: dict) -> dict: ...
    @abstractmethod
    async def get_status(self, external_id: str) -> str: ...
