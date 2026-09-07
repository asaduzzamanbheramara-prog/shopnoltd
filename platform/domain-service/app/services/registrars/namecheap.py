from typing import Any
from xml.etree import ElementTree

import httpx

from app.services.registrar_adapter import RegistrarAdapter

NAMECHEAP_API_PROD = "https://api.namecheap.com/xml.response"
NAMECHEAP_API_SANDBOX = "https://api.sandbox.namecheap.com/xml.response"


class NamecheapAdapter(RegistrarAdapter):
    """Namecheap XML API adapter; credentials never enter returned payloads."""

    def __init__(self, api_key: str, api_secret: str | None = None, username: str | None = None, client_ip: str = "0.0.0.0", sandbox: bool = False):
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
        return {"ApiUser": self.username, "ApiKey": self.api_key, "UserName": self.username, "ClientIp": self.client_ip, "Command": command}

    def _check_response_errors(self, root: ElementTree.Element, operation: str) -> None:
        ns = {"nc": "http://api.namecheap.com/xml.response"}
        errors = root.findall(".//nc:Error", ns)
        if errors:
            raise RuntimeError(f"Namecheap API error in {operation}: {'; '.join((e.text or 'Unknown error').strip() for e in errors)}")
        status = root.get("Status")
        if status and status.lower() != "ok":
            raise RuntimeError(f"Namecheap API {operation} returned Status={status}")

    async def _call(self, command: str, **params: str) -> ElementTree.Element:
        query = self._base_params(command)
        query.update({k: str(v) for k, v in params.items() if v is not None})
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.api_url, params=query)
            response.raise_for_status()
        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError as exc:
            raise RuntimeError("Namecheap returned invalid XML") from exc
        self._check_response_errors(root, command)
        return root

    @staticmethod
    def _parts(domain: str) -> tuple[str, str]:
        labels = domain.strip().lower().split(".")
        if len(labels) < 2 or any(not x for x in labels):
            raise ValueError("valid domain is required")
        return labels[0], ".".join(labels[1:])

    async def check_availability(self, domain: str) -> dict[str, Any]:
        domain = domain.strip().lower()
        root = await self._call("namecheap.domains.check", DomainList=domain)
        node = root.find(".//{http://api.namecheap.com/xml.response}DomainCheckResult")
        return {"domain": domain, "available": bool(node is not None and node.get("Available", "false").lower() == "true"), "premium": bool(node is not None and node.get("IsPremiumName", "false").lower() == "true")}

    async def get_pricing(self, tld: str, years: int = 1) -> dict[str, Any]:
        if years < 1 or years > 10:
            raise ValueError("years must be between 1 and 10")
        tld = tld.strip().lstrip(".").lower()
        root = await self._call("namecheap.users.getPricing", ProductType="DOMAIN", ProductCategory="DOMAINS", ActionName="REGISTER", TLD=tld)
        ns = "{http://api.namecheap.com/xml.response}"
        price = next((float(n.get("Price")) for n in root.findall(f".//{ns}Price") if n.get("Duration") == str(years) and n.get("Price") is not None), None)
        if price is None:
            raise RuntimeError("Namecheap pricing for requested term is unavailable")
        return {"tld": tld, "years": years, "price": price, "currency": "USD"}

    async def register(self, domain: str, years: int, contact: dict[str, Any]) -> dict[str, Any]:
        if years < 1 or years > 10:
            raise ValueError("years must be between 1 and 10")
        sld, tld = self._parts(domain)
        required = ("FirstName", "LastName", "Address1", "City", "StateProvince", "PostalCode", "Country", "Phone", "EmailAddress")
        missing = [k for k in required if not contact.get(k)]
        if missing:
            raise ValueError(f"missing registrar contact fields: {', '.join(missing)}")
        p = {"SLD": sld, "TLD": tld, "Years": str(years)}
        for role in ("Registrant", "Admin", "Tech", "AuxBilling"):
            prefix = "" if role == "Registrant" else role
            p[f"{role}FirstName"] = str(contact.get(f"{prefix}FirstName", contact["FirstName"]))
            p[f"{role}LastName"] = str(contact.get(f"{prefix}LastName", contact["LastName"]))
            p[f"{role}Address1"] = str(contact.get(f"{prefix}Address1", contact["Address1"]))
            p[f"{role}City"] = str(contact.get(f"{prefix}City", contact["City"]))
            p[f"{role}StateProvince"] = str(contact.get(f"{prefix}StateProvince", contact["StateProvince"]))
            p[f"{role}PostalCode"] = str(contact.get(f"{prefix}PostalCode", contact["PostalCode"]))
            p[f"{role}Country"] = str(contact.get(f"{prefix}Country", contact["Country"]))
            p[f"{role}Phone"] = str(contact.get(f"{prefix}Phone", contact["Phone"]))
            p[f"{role}EmailAddress"] = str(contact.get(f"{prefix}EmailAddress", contact["EmailAddress"]))
        root = await self._call("namecheap.domains.create", **p)
        node = root.find(".//{http://api.namecheap.com/xml.response}DomainCreateResult")
        if node is None:
            raise RuntimeError("Namecheap registration response missing DomainCreateResult")
        return {"domain": domain.strip().lower(), "order_id": node.get("OrderID"), "transaction_id": node.get("TransactionID"), "registered": node.get("Registered", "false").lower() == "true", "expires_at": None}

    async def renew(self, domain: str, years: int) -> dict[str, Any]:
        if years < 1 or years > 10:
            raise ValueError("years must be between 1 and 10")
        sld, tld = self._parts(domain)
        root = await self._call("namecheap.domains.renew", SLD=sld, TLD=tld, Years=str(years))
        node = root.find(".//{http://api.namecheap.com/xml.response}DomainRenewResult")
        if node is None or node.get("Renew", "false").lower() != "true":
            raise RuntimeError("Namecheap renewal was not confirmed")
        return {"domain": domain.strip().lower(), "expires_at": node.get("DomainExpirationDate"), "renewed": True}

    async def transfer(self, domain: str, auth_code: str) -> dict[str, Any]:
        if not auth_code or len(auth_code) > 256:
            raise ValueError("valid transfer auth code is required")
        sld, tld = self._parts(domain)
        root = await self._call("namecheap.domains.transfer.create", SLD=sld, TLD=tld, EPPCode=auth_code)
        node = root.find(".//{http://api.namecheap.com/xml.response}DomainTransferResult")
        return {"domain": domain.strip().lower(), "status": node.get("TransferID") if node is not None else "submitted"}

    async def get_nameservers(self, domain: str) -> list[str]:
        sld, tld = self._parts(domain)
        root = await self._call("namecheap.domains.dns.getList", SLD=sld, TLD=tld)
        ns = "{http://api.namecheap.com/xml.response}"
        return [n.get("Address") for n in root.findall(f".//{ns}Nameserver") if n.get("Address")]

    async def set_nameservers(self, domain: str, nameservers: list[str]) -> dict[str, Any]:
        if not nameservers or len(nameservers) > 12:
            raise ValueError("between 1 and 12 nameservers are required")
        sld, tld = self._parts(domain)
        params = {f"Nameserver{i}": v.strip().lower() for i, v in enumerate(nameservers, 1) if v.strip()}
        await self._call("namecheap.domains.dns.setDefault", SLD=sld, TLD=tld, **params)
        return {"domain": domain.strip().lower(), "nameservers": list(params.values())}
