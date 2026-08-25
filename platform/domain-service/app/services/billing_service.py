"""Billing integration for domain registration."""
from decimal import Decimal
import httpx

class BillingService:
    def __init__(self, billing_engine_url: str, payment_service_url: str):
        self.billing_engine_url = billing_engine_url
        self.payment_service_url = payment_service_url

    async def check_wallet_balance(self, user_id: str, tenant_id: str, required_amount: Decimal) -> dict:
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.get(
                f"{self.billing_engine_url}/api/v1/wallet/{user_id}/balance",
                headers={"X-Tenant-ID": tenant_id}
            )
            resp.raise_for_status()
        data = resp.json()
        balance = Decimal(str(data.get("balance", 0)))
        return {"balance": balance, "sufficient": balance >= required_amount}
