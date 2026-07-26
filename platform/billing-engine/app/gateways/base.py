from abc import ABC, abstractmethod
from typing import Any


class GatewayResult(dict):
    """Plain dict subclass so responses stay JSON-serializable, with helpers."""

    @property
    def is_demo(self) -> bool:
        return bool(self.get("is_demo"))


class PaymentGateway(ABC):
    name: str = "base"
    enabled: bool = False  # True only when real credentials are configured

    @abstractmethod
    def create_payment(
        self, amount: float, currency: str, reference: str, **kwargs
    ) -> dict[str, Any]:
        """Start a payment / checkout session. Returns a dict with at least:
        {gateway, is_demo, status, redirect_url|None, gateway_reference}
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
        """Validate an incoming webhook/callback and return the normalized event."""
        raise NotImplementedError
