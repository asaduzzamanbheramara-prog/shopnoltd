"""Billing integration for domain registration."""
from decimal import Decimal
import httpx

class BillingService:
    def __init__(self, billing_engine_url: str, payment_service_url: str, timeout: int = 10):
        self.billing_engine_url = billing_engine_url
        self.payment_service_url = payment_service_url
        self.timeout = timeout

    async def check_wallet_balance(self, user_id: str, tenant_id: str, required_amount: Decimal) -> dict:
        """Check user wallet balance."""
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            resp = await c.get(
                f"{self.billing_engine_url}/api/v1/wallet/{user_id}/balance",
                headers={"X-Tenant-ID": tenant_id}
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Billing service error: {resp.text}")
            data = resp.json()
            balance = Decimal(str(data.get("balance", 0)))
            return {"balance": balance, "sufficient": balance >= required_amount}

    async def deduct_credit(self, user_id: str, tenant_id: str, amount: Decimal, domain: str, years: int, reference_id: str) -> dict:
        """Deduct domain cost from wallet."""
        payload = {
            "user_id": user_id,
            "amount": str(amount),
            "transaction_type": "DOMAIN_REGISTRATION",
            "description": f"Domain registration: {domain} ({years} year(s))",
            "reference_id": reference_id
        }
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            resp = await c.post(
                f"{self.billing_engine_url}/api/v1/wallet/{user_id}/deduct",
                json=payload,
                headers={"X-Tenant-ID": tenant_id}
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Deduction failed: {resp.text}")
            return resp.json()
