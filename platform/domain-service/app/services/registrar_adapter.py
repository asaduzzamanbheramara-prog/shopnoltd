"""Abstract base class every registrar backend must implement."""

from abc import ABC, abstractmethod
from typing import Any


class RegistrarAdapter(ABC):
    """Common interface for all registrar backends (Namecheap, Cloudflare, etc)."""

    def __init__(self, api_key: str, api_secret: str | None = None):
        self.api_key = api_key
        self.api_secret = api_secret

    # ---- Availability ----
    @abstractmethod
    async def check_availability(self, domain: str) -> dict[str, Any]:
        """Return {"domain": str, "available": bool, "premium": bool}"""

    @abstractmethod
    async def get_pricing(self, tld: str, years: int = 1) -> dict[str, Any]:
        """Return {"tld": str, "years": int, "price": float, "currency": str}"""

    # ---- Registration lifecycle ----
    @abstractmethod
    async def register(self, domain: str, years: int, contact: dict[str, Any]) -> dict[str, Any]:
        """Register a domain. Returns {"domain": str, "order_id": str, "expires_at": str}"""

    @abstractmethod
    async def renew(self, domain: str, years: int) -> dict[str, Any]:
        """Renew a domain. Returns {"domain": str, "expires_at": str}"""

    @abstractmethod
    async def transfer(self, domain: str, auth_code: str) -> dict[str, Any]:
        """Initiate an inbound transfer. Returns {"domain": str, "status": str}"""

    # ---- Nameservers / DNS delegation ----
    @abstractmethod
    async def get_nameservers(self, domain: str) -> list[str]:
        """Return list of current nameservers."""

    @abstractmethod
    async def set_nameservers(self, domain: str, nameservers: list[str]) -> dict[str, Any]:
        """Update nameservers. Returns {"domain": str, "nameservers": list[str]}"""
