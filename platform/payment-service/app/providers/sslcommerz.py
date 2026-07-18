"""SSLCommerz — ported from billing-engine/app/gateways/sslcommerz_gateway.py
to payment-service's async BaseProvider interface.
"""

import uuid

import httpx
from app.core.config import settings
from app.providers.base import BaseProvider

API_URLS = {
    True: "https://sandbox.sslcommerz.com/gwprocess/v4/api.php",
    False: "https://securepay.sslcommerz.com/gwprocess/v4/api.php",
}
VALIDATE_URLS = {
    True: "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php",
    False: "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php",
}


class SSLCommerzProvider(BaseProvider):
    def __init__(self):
        super().__init__("sslcommerz")
        self.sandbox = settings.sslcommerz_sandbox
        self.enabled = bool(settings.sslcommerz_store_id and settings.sslcommerz_store_password)

    async def create_deposit(self, tx, return_url=None, **kwargs):
        if not self.enabled:
            return {
                "external_id": f"demo_ssl_{uuid.uuid4().hex[:12]}",
                "redirect_url": None,
                "note": "SSLCommerz not configured (missing store id/password) - running in demo mode.",
            }
        reference = str(tx.id)
        payload = {
            "store_id": settings.sslcommerz_store_id,
            "store_passwd": settings.sslcommerz_store_password,
            "total_amount": f"{float(tx.amount):.2f}",
            "currency": tx.currency.upper(),
            "tran_id": reference,
            "success_url": return_url
            or f"{settings.base_callback_url}/api/v1/webhooks/sslcommerz/success",
            "fail_url": f"{settings.base_callback_url}/api/v1/webhooks/sslcommerz/fail",
            "cancel_url": f"{settings.base_callback_url}/api/v1/webhooks/sslcommerz/cancel",
            "cus_name": kwargs.get("customer_name", "Shopnoltd Customer"),
            "cus_email": kwargs.get("customer_email", "customer@example.com"),
            "cus_add1": kwargs.get("customer_address", "N/A"),
            "cus_phone": kwargs.get("customer_phone", "01700000000"),
            "shipping_method": "NO",
            "product_name": kwargs.get("product_name", "Shopnoltd Order"),
            "product_category": "General",
            "product_profile": "general",
        }
        async with httpx.AsyncClient() as c:
            resp = await c.post(API_URLS[self.sandbox], data=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {
            "external_id": reference,
            "redirect_url": data.get("GatewayPageURL"),
            "raw": data,
        }

    async def create_withdrawal(self, tx, destination, **kwargs):
        raise NotImplementedError(
            "SSLCommerz payouts not supported via this API; use manual withdrawal with admin approval"
        )

    async def verify_webhook(self, request_body: bytes, headers: dict) -> dict:
        # SSLCommerz posts form-encoded IPN data; must additionally call
        # get_status() (val_id validation) before trusting this.
        import urllib.parse

        return dict(urllib.parse.parse_qsl(request_body.decode())) if request_body else {}

    async def get_status(self, external_id: str) -> str:
        # NOTE: SSLCommerz validation actually keys off `val_id` (returned in the
        # IPN/webhook), not `external_id`/tran_id. Pass val_id here when calling
        # this for a real transaction lookup.
        async with httpx.AsyncClient() as c:
            r = await c.get(
                VALIDATE_URLS[self.sandbox],
                params={
                    "val_id": external_id,
                    "store_id": settings.sslcommerz_store_id,
                    "store_passwd": settings.sslcommerz_store_password,
                    "format": "json",
                },
                timeout=15,
            )
        r.raise_for_status()
        return r.json().get("status", "unknown")
