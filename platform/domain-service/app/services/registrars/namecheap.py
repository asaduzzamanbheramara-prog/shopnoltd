from datetime import datetime
from typing import Any
from xml.etree import ElementTree

import httpx

from app.services.registrar_adapter import RegistrarAdapter

NAMECHEAP_API_PROD = "https://api.namecheap.com/xml.response"
NAMECHEAP_API_SANDBOX = "https://api.sandbox.namecheap.com/xml.response"
NS = {"nc": "http://api.namecheap.com/xml.response"}


class NamecheapAdapter(RegistrarAdapter):
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
        return {
            "ApiUser": self.username,
            "ApiKey": self.api_key,
            "UserName": self.username,
            "ClientIp": self.client_ip,
            "Command": command,
        }

    async def _call(self, command: str, **params: Any) -> ElementTree.Element:
        query = self._base_params(command)
        query.update({k: str(v) for k, v in params.items() if v is not None})
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self.api_url, data=query)
            response.raise_for_status()
        root = ElementTree.fromstring(response.text)
        errors = root.findall(".//nc:Error", NS)
        if errors:
            message = "; ".join((e.text or "Unknown error").strip() for e in errors)
            raise RuntimeError(f"Namecheap API error in {command}: {message}")
        if (root.get("Status") or "").lower() != "ok":
            raise RuntimeError(f"Namecheap API {command} returned Status={root.get('Status')}")
        return root

    @staticmethod
    def _split_domain(domain: str) -> tuple[str, str]:
        domain = domain.strip().lower().rstrip(".")
        parts = domain.split(".")
        if len(parts) < 2:
            raise ValueError("Invalid domain")
        return ".".join(parts[:-1]), parts[-1]

    async def check_availability(self, domain: str) -> dict[str, Any]:
        root = await self._call("namecheap.domains.check", DomainList=domain)
        node = root.find(".//nc:DomainCheckResult", NS)
        if node is None:
            raise RuntimeError("Namecheap availability response missing DomainCheckResult")
        return {
            "domain": domain,
            "available": node.get("Available", "false").lower() == "true",
            "premium": node.get("IsPremiumName", "false").lower() == "true",
            "registration_price": node.get("PremiumRegistrationPrice") or None,
            "renewal_price": node.get("PremiumRenewalPrice") or None,
            "currency": "USD",
        }

    async def get_pricing(self, tld: str, years: int = 1) -> dict[str, Any]:
        tld = tld.lstrip(".").lower()
        root = await self._call(
            "namecheap.users.getPricing",
            ProductType="DOMAIN",
            ProductCategory="REGISTER",
            ProductName=tld,
        )
        prices = root.findall(".//nc:ProductCategory[@Name='REGISTER']/nc:Product[@Name='%s']/nc:Price" % tld, NS)
        selected = next((p for p in prices if int(p.get("Duration", "0")) == years), None)
        if selected is None:
            selected = next(iter(prices), None)
        if selected is None:
            raise RuntimeError(f"No Namecheap registration price for .{tld}")
        return {
            "tld": tld,
            "years": int(selected.get("Duration", years)),
            "price": float(selected.get("YourPrice") or selected.get("Price") or 0),
            "currency": selected.get("Currency", "USD"),
        }

    @staticmethod
    def _contact(prefix: str, contact: dict[str, Any]) -> dict[str, str]:
        mapping = {
            "first_name": "FirstName",
            "last_name": "LastName",
            "address1": "Address1",
            "address2": "Address2",
            "city": "City",
            "state": "StateProvince",
            "postal_code": "PostalCode",
            "country": "Country",
            "phone": "Phone",
            "email": "EmailAddress",
            "organization": "OrganizationName",
            "job_title": "JobTitle",
        }
        return {f"{prefix}{target}": str(contact[key]) for key, target in mapping.items() if contact.get(key) is not None}

    async def register(self, domain: str, years: int, contact: dict[str, Any]) -> dict[str, Any]:
        sld, tld = self._split_domain(domain)
        params = {
            "DomainName": domain,
            "Years": years,
            "AddFreeWhoisguard": "no",
            "WGEnabled": "no",
        }
        params.update(self._contact("Registrant", contact))
        params.update(self._contact("Admin", contact.get("admin", contact)))
        params.update(self._contact("Tech", contact.get("tech", contact)))
        params.update(self._contact("AuxBilling", contact.get("billing", contact)))
        if contact.get("nameservers"):
            params["Nameservers"] = ",".join(contact["nameservers"])
        root = await self._call("namecheap.domains.create", **params)
        node = root.find(".//nc:DomainCreateResult", NS)
        if node is None or node.get("Registered", "false").lower() != "true":
            raise RuntimeError("Namecheap did not confirm domain registration")
        return {
            "domain": domain,
            "order_id": node.get("OrderID"),
            "transaction_id": node.get("TransactionID"),
            "domain_id": node.get("DomainID"),
            "charged_amount": node.get("ChargedAmount"),
            "registered": True,
        }

    async def renew(self, domain: str, years: int) -> dict[str, Any]:
        root = await self._call("namecheap.domains.renew", DomainName=domain, Years=years)
        node = root.find(".//nc:DomainRenewResult", NS)
        if node is None or node.get("Renew", "false").lower() != "true":
            raise RuntimeError("Namecheap did not confirm domain renewal")
        details = node.find("nc:DomainDetails", NS)
        return {
            "domain": domain,
            "expires_at": details.get("ExpiredDate") if details is not None else None,
            "order_id": node.get("OrderID"),
            "transaction_id": node.get("TransactionID"),
            "charged_amount": node.get("ChargedAmount"),
        }

    async def transfer(self, domain: str, auth_code: str) -> dict[str, Any]:
        root = await self._call("namecheap.domains.transfer.create", DomainName=domain, EPPCode=auth_code)
        node = root.find(".//nc:DomainTransferCreateResult", NS)
        return {
            "domain": domain,
            "status": (node.get("TransferStatus") if node is not None else "submitted"),
            "order_id": node.get("OrderID") if node is not None else None,
        }

    async def get_nameservers(self, domain: str) -> list[str]:
        sld, tld = self._split_domain(domain)
        root = await self._call("namecheap.domains.dns.getList", SLD=sld, TLD=tld)
        return [n.text.strip() for n in root.findall(".//nc:DomainDNSGetListResult/nc:Nameserver", NS) if n.text]

    async def set_nameservers(self, domain: str, nameservers: list[str]) -> dict[str, Any]:
        if not nameservers:
            raise ValueError("At least one nameserver is required")
        sld, tld = self._split_domain(domain)
        root = await self._call(
            "namecheap.domains.dns.setCustom",
            SLD=sld,
            TLD=tld,
            NameServers=",".join(nameservers),
        )
        node = root.find(".//nc:DomainDNSSetCustomResult", NS)
        if node is None or node.get("Updated", "false").lower() != "true":
            raise RuntimeError("Namecheap did not confirm nameserver update")
        return {"domain": domain, "nameservers": nameservers}
