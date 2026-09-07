"""Server-to-server billing integration for domain purchases."""

from decimal import Decimal

import httpx


class BillingService:
    def __init__(self, billing_engine_url: str, internal_key: str, currency: str = "USD", timeout: int = 15):
        self.billing_engine_url = billing_engine_url.rstrip("/")
        self.internal_key = internal_key
        self.currency = currency.upper()
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        if not self.internal_key:
            raise RuntimeError("billing internal key is not configured")
        return {"X-Internal-Key": self.internal_key}

    async def check_wallet_balance(self, email: str, required_amount: Decimal) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.billing_engine_url}/wallet/{email}",
                params={"currency": self.currency},
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise RuntimeError(f"Billing service error: {response.text}")
            data = response.json()
            balance = Decimal(str(data.get("balance", 0)))
            return {"balance": balance, "sufficient": balance >= required_amount}

    async def deduct_credit(
        self,
        email: str,
        amount: Decimal,
        domain: str,
        years: int,
        reference_id: str,
    ) -> dict:
        payload = {
            "email": email,
            "amount": str(amount),
            "currency": self.currency,
            "reason": f"Domain registration: {domain} ({years} year(s))",
            "reference": reference_id,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.billing_engine_url}/wallet/deduct",
                json=payload,
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise RuntimeError(f"Deduction failed: {response.text}")
            return response.json()

    async def refund_credit(self, email: str, amount: Decimal, reason: str, reference_id: str) -> dict:
        payload = {
            "email": email,
            "amount": str(amount),
            "currency": self.currency,
            "reason": reason,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.billing_engine_url}/wallet/adjust",
                json=payload,
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise RuntimeError(f"Refund failed: {response.text}")
            return response.json()
