"""Billing integration for domain registration.

Domain charges use the payment-service wallet/transaction system and a
stable idempotency key so retries cannot charge the same domain order twice.
"""

from decimal import Decimal
import hashlib

import httpx


class BillingService:
    def __init__(self, payment_service_url: str, platform_wallet_user_id: str, timeout: int = 10):
        self.payment_service_url = payment_service_url.rstrip("/")
        self.platform_wallet_user_id = platform_wallet_user_id
        self.timeout = timeout

    @staticmethod
    def _idempotency_key(domain: str, years: int, currency: str, amount: Decimal) -> str:
        raw = f"domain:{domain.strip().lower()}:{int(years)}:{currency.upper()}:{amount}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def check_wallet_balance(self, user_token: str, currency: str, required_amount: Decimal) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            resp = await c.get(
                f"{self.payment_service_url}/api/v1/wallets/{currency.upper()}",
                headers={"Authorization": f"Bearer {user_token}"},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"payment-service wallet check failed: {resp.text}")
            data = resp.json()
            balance = Decimal(str(data.get("balance", 0)))
            return {"balance": balance, "sufficient": balance >= required_amount}

    async def charge_for_domain(
        self, user_token: str, currency: str, amount: Decimal, domain: str, years: int
    ) -> dict:
        key = self._idempotency_key(domain, years, currency, amount)
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            resp = await c.post(
                f"{self.payment_service_url}/api/v1/transfers",
                headers={"Authorization": f"Bearer {user_token}"},
                json={
                    "to_user_id": self.platform_wallet_user_id,
                    "currency": currency.upper(),
                    "amount": str(amount),
                    "note": f"Domain registration: {domain} ({years}yr)",
                    "idempotency_key": key,
                },
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Domain charge failed: {resp.text}")
            return resp.json()
