import uuid

import requests

from app import config
from app.gateways.base import GatewayResult, PaymentGateway

BASE_URLS = {"sandbox": "https://api-m.sandbox.paypal.com", "live": "https://api-m.paypal.com"}


class PayPalGateway(PaymentGateway):
    name = "paypal"

    def __init__(self):
        self.enabled = config.PAYPAL_ENABLED
        self.base_url = BASE_URLS.get(config.PAYPAL_MODE, BASE_URLS["sandbox"])

    def _get_access_token(self) -> str:
        resp = requests.post(
            f"{self.base_url}/v1/oauth2/token",
            auth=(config.PAYPAL_CLIENT_ID, config.PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def create_payment(
        self, amount: float, currency: str, reference: str, **kwargs
    ) -> GatewayResult:
        if not self.enabled:
            return GatewayResult(
                gateway=self.name,
                is_demo=True,
                status="pending",
                gateway_reference=f"demo_order_{uuid.uuid4().hex[:12]}",
                redirect_url=None,
                note="PayPal not configured (missing PAYPAL_CLIENT_ID/SECRET) - running in demo mode.",
            )
        token = self._get_access_token()
        resp = requests.post(
            f"{self.base_url}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": reference,
                        "amount": {"currency_code": currency.upper(), "value": f"{amount:.2f}"},
                    }
                ],
                "application_context": {
                    "return_url": kwargs.get(
                        "success_url",
                        f"{config.BASE_CALLBACK_URL}/checkout/success?ref={reference}",
                    ),
                    "cancel_url": kwargs.get(
                        "cancel_url", f"{config.BASE_CALLBACK_URL}/checkout/cancel?ref={reference}"
                    ),
                },
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        approve_link = next(
            (l["href"] for l in data.get("links", []) if l["rel"] == "approve"), None
        )
        return GatewayResult(
            gateway=self.name,
            is_demo=False,
            status="pending",
            gateway_reference=data["id"],
            redirect_url=approve_link,
        )

    def capture_order(self, order_id: str) -> dict:
        token = self._get_access_token()
        resp = requests.post(
            f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def verify_webhook(self, payload: bytes, headers: dict) -> dict:
        # PayPal webhook verification requires calling their /v1/notifications/verify-webhook-signature
        # endpoint with the PAYPAL_WEBHOOK_ID. Left as an explicit call from the route handler since it
        # needs the parsed event body; see main.py `/webhook/paypal`.
        raise NotImplementedError
