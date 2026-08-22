"""Cloudflare Registrar adapter.

Docs: https://developers.cloudflare.com/api/operations/registrar-domains-list-domains
Note: Cloudflare Registrar only supports renewals/transfers/nameserver
management for domains already registered through Cloudflare -- it does
NOT support new registrations via API (registration must happen through
their dashboard). check_availability/get_pricing/register raise
NotImplementedError accordingly; callers should route new registrations
to a different adapter (e.g. Namecheap) and use Cloudflare only for
domains already onboarded there.
"""

from typing import Any

import httpx
from app.services.registrar_adapter import RegistrarAdapter

CF_API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareAdapter(RegistrarAdapter):
    def __init__(self, api_key: str, api_secret: str | None = None, account_id: str | None = None):
        super().__init__(api_key, api_secret)
        # For Cloudflare, api_key is expected to be the Bearer token; api_secret unused.
        self.account_id = account_id

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def check_availability(self, domain: str) -> dict[str, Any]:
        raise NotImplementedError(
            "Cloudflare Registrar does not support new-domain availability checks via API; "
            "use a registration-capable adapter (e.g. Namecheap) for new domains."
        )

    async def get_pricing(self, tld: str, years: int = 1) -> dict[str, Any]:
        raise NotImplementedError(
            "Cloudflare Registrar does not support pricing lookups for new registrations via API."
        )

    async def register(self, domain: str, years: int, contact: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            "Cloudflare Registrar does not support new registrations via API."
        )

    async def renew(self, domain: str, years: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.put(
                f"{CF_API_BASE}/accounts/{self.account_id}/registrar/domains/{domain}/renew",
                headers=self._headers(),
                json={"years": years},
            )
        data = resp.json()
        return {"domain": domain, "expires_at": data.get("result", {}).get("expires_at")}

    async def transfer(self, domain: str, auth_code: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.post(
                f"{CF_API_BASE}/accounts/{self.account_id}/registrar/domains/{domain}/transfer",
                headers=self._headers(),
                json={"auth_code": auth_code},
            )
        data = resp.json()
        return {"domain": domain, "status": data.get("result", {}).get("status", "pending")}

    async def get_nameservers(self, domain: str) -> list[str]:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(
                f"{CF_API_BASE}/accounts/{self.account_id}/registrar/domains/{domain}",
                headers=self._headers(),
            )
        data = resp.json()
        return data.get("result", {}).get("name_servers", [])

    async def set_nameservers(self, domain: str, nameservers: list[str]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as c:
            await c.put(
                f"{CF_API_BASE}/accounts/{self.account_id}/registrar/domains/{domain}",
                headers=self._headers(),
                json={"name_servers": nameservers},
            )
        return {"domain": domain, "nameservers": nameservers}
