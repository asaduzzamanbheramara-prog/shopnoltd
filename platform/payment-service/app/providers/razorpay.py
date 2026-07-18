"""Razorpay — implemented with direct async REST calls (httpx) rather than the
official `razorpay` SDK, since that SDK is synchronous and would block the
event loop. Same API Razorpay's SDK wraps: https://razorpay.com/docs/api/
"""

import hashlib
import hmac
import json
import uuid

import httpx
from app.core.config import settings
from app.providers.base import BaseProvider

BASE_URL = "https://api.razorpay.com/v1"


class RazorpayProvider(BaseProvider):
    def __init__(self):
        super().__init__("razorpay")
        self.enabled = bool(settings.razorpay_key_id and settings.razorpay_key_secret)
        self._auth = (settings.razorpay_key_id, settings.razorpay_key_secret)

    async def create_deposit(self, tx, return_url=None, **kwargs):
        if not self.enabled:
            return {
                "external_id": f"demo_order_{uuid.uuid4().hex[:12]}",
                "redirect_url": None,
                "note": "Razorpay not configured (missing key id/secret) - running in demo mode.",
            }
        payload = {
            "amount": int(round(float(tx.amount) * 100)),
            "currency": tx.currency.upper(),
            "receipt": str(tx.id),
            "payment_capture": 1,
        }
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.post(f"{BASE_URL}/orders", json=payload, timeout=15)
        r.raise_for_status()
        order = r.json()
        return {
            "external_id": order["id"],
            # Razorpay uses client-side Checkout.js with this order_id rather
            # than a hosted redirect URL.
            "redirect_url": None,
            "raw": order,
        }

    async def create_withdrawal(self, tx, destination, **kwargs):
        raise NotImplementedError(
            "Razorpay payouts require RazorpayX; use manual withdrawal with admin approval"
        )

    async def verify_webhook(self, request_body: bytes, headers: dict) -> dict:
        if not self.enabled:
            raise RuntimeError("Razorpay not configured")
        signature = headers.get("x-razorpay-signature")
        expected = hmac.new(
            settings.razorpay_key_secret.encode(), request_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature or ""):
            raise ValueError("Invalid Razorpay webhook signature")
        event = json.loads(request_body)
        entity = event["payload"]["payment"]["entity"]
        return {
            "gateway": self.name,
            "external_id": entity.get("order_id"),
            "status": "completed" if entity.get("status") == "captured" else entity.get("status"),
            "amount": (entity.get("amount") or 0) / 100,
            "currency": entity.get("currency"),
        }

    async def get_status(self, external_id: str) -> str:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(f"{BASE_URL}/orders/{external_id}", timeout=15)
        r.raise_for_status()
        return r.json().get("status", "unknown")
