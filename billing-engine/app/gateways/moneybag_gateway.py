from typing import Any

import requests

from app import config
from app.gateways.base import GatewayResult, PaymentGateway

SANDBOX_BASE_URL = "https://sandbox.api.moneybag.com.bd/api/v2"
PRODUCTION_BASE_URL = "https://api.moneybag.com.bd/api/v2"


class MoneybagGateway(PaymentGateway):
    """Moneybag hosted checkout adapter.

    Credentials stay server-side. Checkout creates a hosted session; payment
    state is trusted only after the backend verifies the Moneybag transaction.
    """

    name = "moneybag"

    def __init__(self):
        self.enabled = config.MONEYBAG_ENABLED
        self.sandbox = config.MONEYBAG_SANDBOX

    @property
    def base_url(self) -> str:
        return SANDBOX_BASE_URL if self.sandbox else PRODUCTION_BASE_URL

    def _headers(self) -> dict[str, str]:
        return {
            "X-Merchant-API-Key": config.MONEYBAG_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def create_payment(
        self, amount: float, currency: str, reference: str, **kwargs
    ) -> GatewayResult:
        currency = currency.upper()
        if currency != "BDT":
            raise ValueError("Moneybag currently supports Shopnoltd checkout in BDT only.")
        if amount < 10 or amount > 1_000_000:
            raise ValueError("Moneybag checkout amount must be between 10.00 and 1,000,000.00 BDT.")
        if not self.enabled:
            return GatewayResult(
                gateway=self.name,
                is_demo=True,
                status="pending",
                gateway_reference=reference,
                redirect_url=None,
                note="Moneybag is not configured; sandbox/production credentials are required.",
            )

        base_callback = config.BASE_CALLBACK_URL.rstrip("/")
        payload = {
            "order_id": reference,
            "order_amount": f"{amount:.2f}",
            "currency": currency,
            "order_description": kwargs.get("product_name", "Shopnoltd Order")[:255],
            "success_url": kwargs.get(
                "success_url", f"{base_callback}/webhook/moneybag/success"
            ),
            "cancel_url": kwargs.get(
                "cancel_url", f"{base_callback}/webhook/moneybag/cancel"
            ),
            "fail_url": kwargs.get(
                "fail_url", f"{base_callback}/webhook/moneybag/fail"
            ),
            "ipn_url": kwargs.get(
                "ipn_url", f"{base_callback}/webhook/moneybag/ipn"
            ),
            "customer": {
                "name": kwargs.get("customer_name") or "Shopnoltd Customer",
                "email": kwargs.get("customer_email") or "customer@example.com",
                "phone": kwargs.get("customer_phone") or "+8801700000000",
                "address": kwargs.get("customer_address") or "Dhaka",
                "city": kwargs.get("customer_city") or "Dhaka",
                "postcode": kwargs.get("customer_postcode") or "1000",
                "country": "Bangladesh",
            },
        }
        response = requests.post(
            f"{self.base_url}/payments/checkout",
            json=payload,
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") or {}
        checkout_url = data.get("checkout_url")
        session_id = data.get("session_id")
        if not body.get("success") or not checkout_url or not session_id:
            raise RuntimeError(f"Moneybag checkout did not return a hosted checkout session: {body}")

        return GatewayResult(
            gateway=self.name,
            is_demo=False,
            status="pending",
            gateway_reference=reference,
            redirect_url=checkout_url,
            session_id=session_id,
            expires_at=data.get("expires_at"),
            raw=body,
        )

    def verify_transaction(self, transaction_id: str) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Moneybag is not configured")
        response = requests.get(
            f"{self.base_url}/payments/verify/{transaction_id}",
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("success"):
            raise RuntimeError(f"Moneybag verification failed: {body}")
        return body

    def verify_webhook(self, payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
        raise NotImplementedError(
            "Moneybag webhook signature verification is handled by the webhook boundary; "
            "payment state must still be verified server-side."
        )
