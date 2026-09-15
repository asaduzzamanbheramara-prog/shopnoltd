"""Nagad Merchant API provider.

Customer payments may originate from ordinary Nagad customer accounts. The
merchant-side credentials belong to Shopnoltd and are used only by this
backend. Missing production credentials never create a fake/demo transaction.
"""

from __future__ import annotations

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

SUCCESS_STATUSES = {"SUCCESS", "COMPLETED", "PAID", "SUCCESSFUL"}


class NagadProvider(BaseProvider):
    def __init__(self):
        super().__init__("nagad")
        self.sandbox = settings.nagad_sandbox
        self.base_url = BASE_URLS[self.sandbox]
        self.enabled = bool(
            settings.nagad_merchant_id
            and settings.nagad_merchant_private_key
            and settings.nagad_pg_public_key
        )

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

    @staticmethod
    def _callback_url() -> str:
        return f"{settings.base_callback_url.rstrip('/')}/api/v1/webhooks/nagad"

    async def create_deposit(self, tx, return_url=None, **kwargs):
        if not self.enabled:
            raise RuntimeError("Nagad is not configured: merchant ID and RSA keys are required")
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
        async with httpx.AsyncClient(timeout=15) as client:
            init_resp = await client.post(
                f"{self.base_url}/check-out/initialize/{settings.nagad_merchant_id}/{order_id}",
                json=init_payload,
                headers={"X-KM-IP-V4": customer_ip, "X-KM-Client-Type": "PC_WEB"},
            )
        init_resp.raise_for_status()
        init_data = init_resp.json()
        payment_ref_id = init_data.get("paymentReferenceId")
        challenge = init_data.get("challenge")
        if not payment_ref_id or not challenge:
            raise RuntimeError("Nagad did not return a payment reference/challenge")

        complete_sensitive = (
            f"merchantId={settings.nagad_merchant_id}&orderId={order_id}&currencyCode=050"
            f"&amount={float(tx.amount):.2f}&challenge={challenge}"
        )
        complete_payload = {
            "sensitiveData": self._encrypt(complete_sensitive),
            "signature": self._sign(complete_sensitive),
            "merchantCallbackURL": self._callback_url(),
        }
        async with httpx.AsyncClient(timeout=15) as client:
            complete_resp = await client.post(
                f"{self.base_url}/check-out/complete/{payment_ref_id}",
                json=complete_payload,
                headers={"X-KM-IP-V4": customer_ip, "X-KM-Client-Type": "PC_WEB"},
            )
        complete_resp.raise_for_status()
        complete_data = complete_resp.json()
        redirect_url = complete_data.get("callBackUrl") or complete_data.get("callbackUrl")
        if not redirect_url:
            raise RuntimeError("Nagad did not return a checkout URL")
        return {"external_id": str(payment_ref_id), "redirect_url": redirect_url}

    async def create_withdrawal(self, tx, destination, **kwargs):
        raise NotImplementedError(
            "Nagad payouts require an approved Nagad disbursement integration; customer accounts do not need to be merchants"
        )

    async def verify_webhook(self, request_body: bytes, headers: dict) -> dict:
        import json

        data = json.loads(request_body) if request_body else {}
        payment_ref_id = (
            data.get("payment_ref_id")
            or data.get("paymentReferenceId")
            or data.get("paymentID")
        )
        if not payment_ref_id:
            raise ValueError("Nagad callback is missing payment reference")
        return await self.confirm_callback(str(payment_ref_id))

    async def confirm_callback(self, external_id: str) -> dict:
        status_data = await self.payment_details(external_id)
        return {**status_data, "paymentReferenceId": str(external_id)}

    async def payment_details(self, external_id: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{self.base_url}/verify/payment/{external_id}")
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("Nagad verification returned an invalid response")
        return data

    async def get_status(self, external_id: str) -> str:
        data = await self.payment_details(external_id)
        return str(data.get("status") or data.get("transactionStatus") or "UNKNOWN").upper()
