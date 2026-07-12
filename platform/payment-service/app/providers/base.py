"""Base payment provider."""
from abc import ABC, abstractmethod
from typing import Tuple
class BaseProvider(ABC):
    def __init__(self, name: str): self.name = name
    @abstractmethod
    async def create_deposit(self, tx, **kwargs) -> dict: ...
    @abstractmethod
    async def create_withdrawal(self, tx, **kwargs) -> dict: ...
    @abstractmethod
    async def verify_webhook(self, request_body: bytes, headers: dict) -> dict: ...
    @abstractmethod
    async def get_status(self, external_id: str) -> str: ...

