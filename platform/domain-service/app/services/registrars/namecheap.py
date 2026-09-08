from typing import Any
from xml.etree import ElementTree
import httpx
from app.services.registrar_adapter import RegistrarAdapter

NAMECHEAP_API_PROD = "https://api.namecheap.com/xml.response"
NAMECHEAP_API_SANDBOX = "https://api.sandbox.namecheap.com/xml.response"
NS = {"nc": "http://api.namecheap.com/xml.response"}


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
        errors = root.findall(".//nc:Error", NS)
        if errors:
            messages = [(error.text or "Unknown error").strip() for error in errors]
            message = "; ".join(messages)
            raise RuntimeError(f"Namecheap API error in {operation}: {message}")
        status = root.get("Status")
        if status and status.lower() != "ok":
            raise RuntimeError(f"Namecheap API {operation} returned Status={status}")

    async def _call(self, command: str, params: dict[str, str], operation: str) -> ElementTree.Element:
        payload = {**self._base_params(command), **params}
        async with httpx.AsyncClient(timeout=20) as c:
            resp = await c.get(self.api_url, params=payload)
            resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
        self._check_response_errors(root, operation)
        return root

    # ---- Availability ----------------------------------------------------
    async def check_availability(self, domain: str) -> dict[str, Any]:
        root = await self._call(
            "namecheap.domains.check", {"DomainList": domain}, "check_availability"
        )
        node = root.find(".//nc:DomainCheckResult", NS)
        if node is None:
            raise RuntimeError(f"Namecheap check_availability: no result for {domain}")
        return {
            "domain": node.get("Domain", domain),
            "available": node.get("Available", "false").lower() == "true",
            "premium": node.get("IsPremiumName", "false").lower() == "true",
            "premium_price": (
                float(node.get("PremiumRegistrationPrice"))
                if node.get("PremiumRegistrationPrice")
                else None
            ),
        }

    async def get_pricing(self, tld: str, years: int = 1) -> dict[str, Any]:
        tld = tld.lstrip(".")
        root = await self._call(
            "namecheap.users.getPricing",
            {"ProductType": "DOMAIN", "ProductCategory": "REGISTER", "ProductName": tld},
            "get_pricing",
        )
        # Structure: UserGetPricingResult/ProductType/ProductCategory/Product/Price[Duration="1"]
        price_node = None
        for price in root.findall(".//nc:Product/nc:Price", NS):
            if price.get("Duration") == str(years) and price.get("DurationType", "YEAR") == "YEAR":
                price_node = price
                break
        if price_node is None:
            # Fall back to the first available duration if an exact match isn't found
            price_node = root.find(".//nc:Product/nc:Price", NS)
        if price_node is None:
            raise RuntimeError(f"Namecheap get_pricing: no pricing returned for .{tld}")
        return {
            "tld": tld,
            "years": years,
            "price": float(price_node.get("YourPrice") or price_node.get("Price")),
            "currency": price_node.get("Currency", "USD"),
        }

    # ---- Registration lifecycle -------------------------------------------
    def _contact_params(self, contact: dict[str, Any], prefix: str) -> dict[str, str]:
        # Namecheap requires Registrant/Tech/Admin/AuxBilling contact blocks.
        # We use the same contact dict for all four roles unless the caller
        # supplied role-specific overrides.
        return {
            f"{prefix}FirstName": contact["first_name"],
            f"{prefix}LastName": contact["last_name"],
            f"{prefix}Address1": contact["address1"],
            f"{prefix}City": contact["city"],
            f"{prefix}StateProvince": contact["state"],
            f"{prefix}PostalCode": contact["postal_code"],
            f"{prefix}Country": contact["country"],
            f"{prefix}Phone": contact["phone"],
            f"{prefix}EmailAddress": contact["email"],
        }

    async def register(self, domain: str, years: int, contact: dict[str, Any]) -> dict[str, Any]:
        required = [
            "first_name", "last_name", "address1", "city", "state",
            "postal_code", "country", "phone", "email",
        ]
        missing = [f for f in required if not contact.get(f)]
        if missing:
            raise ValueError(f"Missing required registrant contact fields: {', '.join(missing)}")

        params: dict[str, str] = {"DomainName": domain, "Years": str(years)}
        for prefix in ("Registrant", "Tech", "Admin", "AuxBilling"):
            params.update(self._contact_params(contact, prefix))
        params["AddFreeWhoisguard"] = "yes"
        params["WGEnabled"] = "yes"

        root = await self._call("namecheap.domains.create", params, "register")
        node = root.find(".//nc:DomainCreateResult", NS)
        if node is None or node.get("Registered", "false").lower() != "true":
            raise RuntimeError(f"Namecheap register: registration not confirmed for {domain}")
        return {
            "domain": domain,
            "order_id": node.get("OrderID", ""),
            "transaction_id": node.get("TransactionID", ""),
            # Namecheap doesn't return an expiry date on create; caller should
            # compute expires_at = now + years, or fetch it via a follow-up
            # namecheap.domains.getInfo call if exact registrar-side date matters.
        }

    async def renew(self, domain: str, years: int) -> dict[str, Any]:
        root = await self._call(
            "namecheap.domains.renew",
            {"DomainName": domain, "Years": str(years)},
            "renew",
        )
        node = root.find(".//nc:DomainRenewResult", NS)
        if node is None or node.get("Renew", "false").lower() != "true":
            raise RuntimeError(f"Namecheap renew: renewal not confirmed for {domain}")
        return {"domain": domain, "order_id": node.get("OrderID", ""), "expires_at": None}

    async def transfer(self, domain: str, auth_code: str) -> dict[str, Any]:
        root = await self._call(
            "namecheap.domains.transfer.create",
            {"DomainName": domain, "EPPCode": auth_code, "Years": "1"},
            "transfer",
        )
        node = root.find(".//nc:DomainTransferAddResult", NS)
        status = "pending" if node is not None else "unknown"
        return {"domain": domain, "status": status}

    # ---- Nameservers -------------------------------------------------------
    async def get_nameservers(self, domain: str) -> list[str]:
        sld, _, tld = domain.partition(".")
        root = await self._call(
            "namecheap.domains.dns.getList",
            {"SLD": sld, "TLD": tld},
            "get_nameservers",
        )
        return [ns.text for ns in root.findall(".//nc:Nameserver", NS) if ns.text]

    async def set_nameservers(self, domain: str, nameservers: list[str]) -> dict[str, Any]:
        sld, _, tld = domain.partition(".")
        root = await self._call(
            "namecheap.domains.dns.setCustom",
            {"SLD": sld, "TLD": tld, "Nameservers": ",".join(nameservers)},
            "set_nameservers",
        )
        node = root.find(".//nc:DomainDNSSetCustomResult", NS)
        ok = node is not None and node.get("Update", "false").lower() == "true"
        if not ok:
            raise RuntimeError(f"Namecheap set_nameservers: update not confirmed for {domain}")
        return {"domain": domain, "nameservers": nameservers}
