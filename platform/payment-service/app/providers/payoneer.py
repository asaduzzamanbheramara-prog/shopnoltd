"""Payoneer provider — PAYOUTS ONLY.

Payoneer has no customer-facing checkout API; it's built for paying money
out (seller payouts, affiliate/freelancer payments, mass payouts). Only
create_withdrawal is implemented. create_deposit intentionally raises —
if a customer needs to pay in, use PayPal/Stripe/crypto instead.
"""

import httpx

from app.core.config import settings
from app.providers.base import BaseProvider

BASE_URLS = {
    True: "https://api.sandbox.payoneer.com/v2",
    False: "https://api.payoneer.com/v2",
}


class PayoneerProvider(BaseProvider):
    def __init__(self):
        super().__init__("payoneer")
        self.enabled = bool(
            settings.payoneer_program_id
            and settings.payoneer_api_username
            and settings.payoneer_api_password
        )
        self.base_url = BASE_URLS[settings.payoneer_sandbox]

    async def create_deposit(self, tx, **kwargs):
        raise NotImplementedError("Payoneer has no customer-facing checkout API; deposits are not supported.")

    async def create_withdrawal(self, tx, payee_id=None, description=None, **kwargs):
        if not payee_id:
            raise ValueError("Payoneer payouts require a payee_id.")

        if not self.enabled:
            return {
                "external_id": f"demo-payout-{tx.id}",
                "status": "pending",
                "note": "Payoneer not configured (missing program id / API credentials) - demo mode.",
            }

        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.post(
                f"{self.base_url}/programs/{settings.payoneer_program_id}/payouts",
                auth=(settings.payoneer_api_username, settings.payoneer_api_password),
                json={
                    "payee_id": payee_id,
                    "amount": f"{tx.amount:.2f}",
                    "currency": tx.currency.upper(),
                    "description": description or f"Shopnoltd payout {tx.id}",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "external_id": data.get("payout_id", f"payoneer-{tx.id}"),
            "status": data.get("status", "submitted"),
            "raw": data,
        }

    async def verify_webhook(self, body, headers):
        import json
        return json.loads(body.decode("utf-8"))

    async def get_status(self, external_id):
        if not self.enabled:
            return "demo"
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(
                f"{self.base_url}/programs/{settings.payoneer_program_id}/payouts/{external_id}",
                auth=(settings.payoneer_api_username, settings.payoneer_api_password),
            )
            resp.raise_for_status()
            return resp.json().get("status", "unknown")
