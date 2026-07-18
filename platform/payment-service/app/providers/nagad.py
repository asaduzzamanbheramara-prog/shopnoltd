"""Nagad Merchant API — ported from billing-engine/app/gateways/nagad_gateway.py
to payment-service's async BaseProvider interface.

Nagad signs/encrypts every request with RSA keypairs exchanged with Nagad
during merchant onboarding (your private key + Nagad's public key).
Requires the `cryptography` package (already in requirements.txt).
"""

import base64
import datetime
import uuid

import httpx
from app.core.config import settings
from app.providers.base import BaseProvider

BASE_URLS = {
    True: "http://sandbox.mynagad.com:10080/remote-payment-gateway-1.0/api/dfs",
    False: "https://api.mynagad.com/api/dfs",
}


class NagadProvider(BaseProvider):
    def __init__(self):
        super().__init__("nagad")
        self.sandbox = settings.nagad_sandbox
        self.base_url = BASE_URLS[self.sandbox]
        self.enabled = bool(settings.nagad_merchant_id and settings.nagad_merchant_private_key)

    def _sign(self, data: str) -> str:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        private_key = serialization.load_pem_private_key(
            settings.nagad_merchant_private_key.encode(),
            password=None,
        )
        signature = private_key.sign(data.encode(), padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode()

    def _encrypt(self, data: str) -> str:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        public_key = serialization.load_pem_public_key(settings.nagad_pg_public_key.encode())
        encrypted = public_key.encrypt(data.encode(), padding.PKCS1v15())
        return base64.b64encode(encrypted).decode()

    async def create_deposit(self, tx, return_url=None, **kwargs):
        if not self.enabled:
            return {
                "external_id": f"demo_nagad_{uuid.uuid4().hex[:12]}",
                "redirect_url": None,
                "note": "Nagad not configured (missing merchant id/RSA keys) - running in demo mode.",
            }
        if tx.currency.upper() != "BDT":
            raise ValueError("Nagad only supports BDT")

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        order_id = str(tx.id)
        customer_ip = kwargs.get("customer_ip", "127.0.0.1")

        sensitive = (
            f"merchantId={settings.nagad_merchant_id}&datetime={timestamp}"
            f"&orderId={order_id}&challenge={uuid.uuid4().hex}"
        )
        init_payload = {
            "accountNumber": settings.nagad_merchant_id,
            "dateTime": timestamp,
            "sensitiveData": self._encrypt(sensitive),
            "signature": self._sign(sensitive),
        }
        async with httpx.AsyncClient() as c:
            init_resp = await c.post(
                f"{self.base_url}/check-out/initialize/{settings.nagad_merchant_id}/{order_id}",
                json=init_payload,
                headers={"X-KM-IP-V4": customer_ip, "X-KM-Client-Type": "PC_WEB"},
                timeout=15,
            )
        init_resp.raise_for_status()
        init_data = init_resp.json()
        payment_ref_id = init_data.get("paymentReferenceId")
        challenge = init_data.get("challenge")

        complete_sensitive = (
            f"merchantId={settings.nagad_merchant_id}&orderId={order_id}&currencyCode=050"
            f"&amount={float(tx.amount):.2f}&challenge={challenge}"
        )
        complete_payload = {
            "sensitiveData": self._encrypt(complete_sensitive),
            "signature": self._sign(complete_sensitive),
            "merchantCallbackURL": f"{settings.base_callback_url}/api/v1/webhooks/nagad",
        }
        async with httpx.AsyncClient() as c:
            complete_resp = await c.post(
                f"{self.base_url}/check-out/complete/{payment_ref_id}",
                json=complete_payload,
                headers={"X-KM-IP-V4": customer_ip, "X-KM-Client-Type": "PC_WEB"},
                timeout=15,
            )
        complete_resp.raise_for_status()
        complete_data = complete_resp.json()
        return {
            "external_id": payment_ref_id,
            "redirect_url": complete_data.get("callBackUrl"),
        }

    async def create_withdrawal(self, tx, destination, **kwargs):
        raise NotImplementedError(
            "Nagad payouts not supported via this API; use manual withdrawal with admin approval"
        )

    async def verify_webhook(self, request_body: bytes, headers: dict) -> dict:
        # Nagad redirects to merchantCallbackURL with payment_ref_id & status query params;
        # the caller must then call get_status() to confirm before trusting this.
        import json

        return json.loads(request_body) if request_body else {}

    async def get_status(self, external_id: str) -> str:
        async with httpx.AsyncClient() as c:
            r = await c.get(
                f"{self.base_url}/verify/payment/{external_id}",
                timeout=15,
            )
        r.raise_for_status()
        return r.json().get("status", "unknown")
