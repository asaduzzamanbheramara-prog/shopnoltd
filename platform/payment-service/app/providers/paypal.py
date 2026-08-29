"""PayPal provider — customer-facing checkout (deposits)."""

import httpx

from app.core.config import settings
from app.providers.base import BaseProvider

BASE_URLS = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live": "https://api-m.paypal.com",
}


class PayPalProvider(BaseProvider):
    def __init__(self):
        super().__init__("paypal")
        self.enabled = bool(settings.paypal_client_id and settings.paypal_secret)
        self.base_url = BASE_URLS.get(settings.paypal_mode, BASE_URLS["sandbox"])

    async def _get_access_token(self) -> str:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=(settings.paypal_client_id, settings.paypal_secret),
                data={"grant_type": "client_credentials"},
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def create_deposit(self, tx, return_url=None, **kwargs):
        if not self.enabled:
            return {
                "external_id": f"demo-{tx.id}",
                "status": "pending",
                "redirect_url": None,
                "note": "PayPal not configured (missing paypal_client_id/secret) - demo mode.",
            }

        token = await self._get_access_token()
        cancel_url = kwargs.get("cancel_url", f"{settings.base_callback_url}/checkout/cancel?ref={tx.id}")
        success_url = return_url or f"{settings.base_callback_url}/checkout/success?ref={tx.id}"

        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.post(
                f"{self.base_url}/v2/checkout/orders",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [
                        {
                            "reference_id": str(tx.id),
                            "amount": {
                                "currency_code": tx.currency.upper(),
                                "value": f"{tx.amount:.2f}",
                            },
                        }
                    ],
                    "application_context": {
                        "return_url": success_url,
                        "cancel_url": cancel_url,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()

        approve_link = next(
            (l["href"] for l in data.get("links", []) if l["rel"] == "approve"), None
        )
        return {
            "external_id": data["id"],
            "status": "pending",
            "redirect_url": approve_link,
        }

    async def create_withdrawal(self, tx, **kwargs):
        raise NotImplementedError("PayPal is deposit-only in this integration; use Payoneer for payouts.")

    async def verify_webhook(self, body, headers):
        # Full verification requires calling PayPal's /v1/notifications/verify-webhook-signature
        # with a configured webhook ID. Returning the raw payload for the route handler to process
        # until that's wired up — do not treat this as verified/trusted yet.
        import json
        return json.loads(body.decode("utf-8"))

    async def get_status(self, external_id):
        if not self.enabled:
            return "demo"
        token = await self._get_access_token()
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(
                f"{self.base_url}/v2/checkout/orders/{external_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json().get("status", "unknown")
