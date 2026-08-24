"""Namecheap registrar adapter with error handling and sandbox support."""

from typing import Any
from xml.etree import ElementTree

import httpx
from app.services.registrar_adapter import RegistrarAdapter

NAMECHEAP_API_PROD = "https://api.namecheap.com/xml.response"
NAMECHEAP_API_SANDBOX = "https://sandbox.namecheap.com/xml.response"


class NamecheapAdapter(RegistrarAdapter):
    def __init__(
        self,
        api_key: str,
        api_secret: str | None = None,
        username: str | None = None,
        client_ip: str = "0.0.0.0",
        sandbox: bool = False,
    ):
        super().__init__(api_key, api_secret)
        if not username:
            raise ValueError("Namecheap username is required")
        if not client_ip or client_ip == "0.0.0.0":
            raise ValueError("Namecheap client IP is required")
        self.username = username
        self.client_ip = client_ip
        self.sandbox = sandbox
        self.api_url = NAMECHEAP_API_SANDBOX if sandbox else NAMECHEAP_API_PROD

    def _base_params(self, command: str) -> dict[str, str]:
        return {
            "ApiUser": self.username,
            "ApiKey": self.api_key,
            "UserName": self.username,
            "ClientIp": self.client_ip,
            "Command": command,
        }

    def _check_response_errors(self, root, operation: str) -> None:
        ns = {"nc": "http://api.namecheap.com/xml.response"}
        errors = root.findall(".//nc:Error", ns)
        if errors:
            messages = [(error.text or "Unknown error").strip() for error in errors]
            raise RuntimeError(f"Namecheap API error in {operation}: {'; '.join(messages)}")
        status = root.get("Status")
        if status and status.lower() != "ok":
            raise RuntimeError(f"Namecheap API {operation} returned Status={status}")

    async def check_availability(self, domain: str) -> dict[str, Any]:
        params = self._base_params("namecheap.domains.check")
        params["DomainList"] = domain
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(self.api_url, params=params)
            resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
        self._check_response_errors(root, "check_availability")
        ns = {"nc": "http://api.namecheap.com/xml.response"}
        result = root.find(".//nc:DomainCheckResult", ns)
        if result is None:
            raise RuntimeError("Namecheap API response did not contain DomainCheckResult")
        return {
            "domain": domain,
            "available": result.get("Available") == "true",
            "premium": result.get("IsPremiumName") == "true",
        }

    async def get_pricing(self, tld: str, years: int = 1) -> dict[str, Any]:
        params = self._base_params("namecheap.users.getPricing")
        params["ProductType"] = "DOMAIN"
        params["ProductCategory"] = "REGISTER"
        params["ActionName"] = "REGISTER"
        params["ProductName"] = tld.lstrip(".")
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(self.api_url, params=params)
            resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
        self._check_response_errors(root, "get_pricing")
        ns = {"nc": "http://api.namecheap.com/xml.response"}
        price_el = root.find(".//nc:Price", ns)
        price = float(price_el.get("Price")) if price_el is not None else 0.0
        return {"tld": tld, "years": years, "price": price * years, "currency": "USD"}

    async def register(self, domain: str, years: int, contact: dict[str, Any]) -> dict[str, Any]:
        params = self._base_params("namecheap.domains.create")
        params["DomainName"] = domain
        params["Years"] = str(years)
        for role in ("Registrant", "Tech", "Admin", "AuxBilling"):
            for field, value in contact.items():
                params[f"{role}{field}"] = str(value)
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.get(self.api_url, params=params)
            resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
        self._check_response_errors(root, "register")
        ns = {"nc": "http://api.namecheap.com/xml.response"}
        result = root.find(".//nc:DomainCreateResult", ns)
        if result is None:
            raise RuntimeError("Namecheap API response did not contain DomainCreateResult")
        return {
            "domain": domain,
            "order_id": result.get("OrderID"),
            "expires_at": result.get("ExpirationDate"),
        }

    async def renew(self, domain: str, years: int) -> dict[str, Any]:
        params = self._base_params("namecheap.domains.renew")
        params["DomainName"] = domain
        params["Years"] = str(years)
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.get(self.api_url, params=params)
            resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
        self._check_response_errors(root, "renew")
        ns = {"nc": "http://api.namecheap.com/xml.response"}
        result = root.find(".//nc:DomainRenewResult", ns)
        return {
            "domain": domain,
            "expires_at": result.get("ExpirationDate") if result is not None else None,
        }

    async def transfer(self, domain: str, auth_code: str) -> dict[str, Any]:
        params = self._base_params("namecheap.domains.transfer.create")
        params["DomainName"] = domain
        params["EPPCode"] = auth_code
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.get(self.api_url, params=params)
            resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
        self._check_response_errors(root, "transfer")
        return {"domain": domain, "status": "pending"}

    async def get_nameservers(self, domain: str) -> list[str]:
        sld, _, tld = domain.partition(".")
        params = self._base_params("namecheap.domains.dns.getList")
        params["SLD"] = sld
        params["TLD"] = tld
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(self.api_url, params=params)
            resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
        self._check_response_errors(root, "get_nameservers")
        ns = {"nc": "http://api.namecheap.com/xml.response"}
        return [el.text for el in root.findall(".//nc:Nameserver", ns) if el.text]

    async def set_nameservers(self, domain: str, nameservers: list[str]) -> dict[str, Any]:
        sld, _, tld = domain.partition(".")
        params = self._base_params("namecheap.domains.dns.setCustom")
        params["SLD"] = sld
        params["TLD"] = tld
        params["Nameservers"] = ",".join(nameservers)
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(self.api_url, params=params)
            resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
        self._check_response_errors(root, "set_nameservers")
        return {"domain": domain, "nameservers": nameservers}
