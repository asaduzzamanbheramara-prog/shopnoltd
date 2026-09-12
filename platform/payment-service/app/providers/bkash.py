"""bKash Tokenized Checkout provider.

Customers may pay from their own ordinary bKash accounts. The Shopnoltd
credentials identify Shopnoltd as the receiving business; customer numbers
are never required to be merchant credentials.
"""

from __future__ import annotations

from urllib.parse import urljoin

import httpx
from app.core.config import settings
from app.providers.base import BaseProvider

BASE_URL = "https://tokenized.pay.bka.sh/v1.2.0-beta/"
TOKEN_URL = urljoin(BASE_URL, "tokenized/checkout/token/grant")
CREATE_URL = urljoin(BASE_URL, "tokenized/checkout/create")
EXECUTE_URL = urljoin(BASE_URL, "tokenized/checkout/execute")
STATUS_URL = urljoin(BASE_URL, "tokenized/checkout/payment/status")

SUCCESS_STATUSES = {"COMPLETED", "SUCCESS", "PAID", "CAPTURED"}


class BkashProvider(BaseProvider):
    def __init__(self):
        super().__init__("bkash")
        self.enabled = bool(
            settings.bkash_app_key
            and settings.bkash_app_secret
            and settings.bkash_username
            and settings.bkash_password
        )

    async def _token(self) -> str:
        if not self.enabled:
            raise RuntimeError("bKash is not configured: app key/secret and username/password are required")

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                TOKEN_URL,
                json={
                    "app_key": settings.bkash_app_key,
                    "app_secret": settings.bkash_app_secret,
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "username": settings.bkash_username,
                    "password": settings.bkash_password,
                },
            )
        response.raise_for_status()
        data = response.json()
        token = data.get("id_token")
        if not token:
            raise RuntimeError(data.get("statusMessage") or "bKash did not return an id_token")
        return token

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": token,
            "X-APP-Key": settings.bkash_app_key,
        }

    @staticmethod
    def _callback_url() -> str:
        return f"{settings.base_callback_url.rstrip('/')}/api/v1/webhooks/bkash"

    async def create_deposit(self, tx, return_url=None, **kwargs):
        if tx.currency.upper() != "BDT":
            raise ValueError("bKash only supports BDT")

        token = await self._token()
        payload = {
            "mode": "0011",
            "payerReference": str(tx.user_id),
            "callbackURL": self._callback_url(),
            "amount": f"{float(tx.amount):.2f}",
            "currency": "BDT",
            "intent": "sale",
            "merchantInvoiceNumber": str(tx.id),
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(CREATE_URL, json=payload, headers=self._headers(token))
        response.raise_for_status()
        data = response.json()
        payment_id = data.get("paymentID")
        redirect_url = data.get("bkashURL")
        if not payment_id or not redirect_url:
            raise RuntimeError(data.get("statusMessage") or "bKash did not return a payment session")

        return {
            "external_id": str(payment_id),
            "redirect_url": redirect_url,
            "approval_url": redirect_url,
        }

    async def execute_payment(self, payment_id: str) -> dict:
        token = await self._token()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                EXECUTE_URL,
                json={"paymentID": payment_id},
                headers=self._headers(token),
            )
        response.raise_for_status()
        return response.json()

    async def payment_status(self, payment_id: str) -> dict:
        token = await self._token()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                STATUS_URL,
                json={"paymentID": payment_id},
                headers=self._headers(token),
            )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("bKash status response is invalid")
        return data

    async def confirm_callback(self, payment_id: str) -> dict:
        """Confirm a checkout without executing an already-completed payment twice."""
        current = await self.payment_status(payment_id)
        current_status = str(
            current.get("transactionStatus") or current.get("status") or ""
        ).upper()
        if current_status not in SUCCESS_STATUSES:
            executed = await self.execute_payment(payment_id)
            current = await self.payment_status(payment_id)
            current["execute"] = executed
        current["paymentID"] = str(payment_id)
        return current

    async def create_withdrawal(self, tx, destination, **kwargs):
        raise NotImplementedError(
            "bKash payouts require an approved bKash B2C/B2B payout integration; customer accounts do not need to be merchants"
        )

    async def verify_webhook(self, body: bytes, headers: dict) -> dict:
        import json

        data = json.loads(body) if body else {}
        payment_id = data.get("paymentID") or data.get("paymentId")
        if not payment_id:
            raise ValueError("bKash callback is missing paymentID")
        return await self.confirm_callback(str(payment_id))

    async def get_status(self, external_id: str) -> str:
        data = await self.payment_status(str(external_id))
        return str(data.get("transactionStatus") or data.get("status") or "PENDING").upper()
