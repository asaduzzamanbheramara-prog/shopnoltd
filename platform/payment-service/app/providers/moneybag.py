"""Moneybag hosted-checkout provider for the wallet/payment service."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import httpx

from app.core.config import settings
from app.providers.base import BaseProvider

BASE_URLS = {
    "sandbox": "https://sandbox.api.moneybag.com.bd",
    "live": "https://api.moneybag.com.bd",
}


class MoneybagProvider(BaseProvider):
    def __init__(self):
        super().__init__("moneybag")
        self.enabled = bool(settings.moneybag_api_key)
        self.base_url = BASE_URLS.get(settings.moneybag_mode, BASE_URLS["sandbox"])

    async def create_deposit(self, tx, return_url=None, **kwargs):
        if not self.enabled:
            return {
                "external_id": None,
                "status": "pending",
                "redirect_url": None,
                "is_demo": True,
                "note": "Moneybag is not configured; no payment was sent.",
            }

        reference = kwargs.get("reference") or str(tx.id)
        payload = {
            "order_id": reference,
            "order_amount": f"{tx.amount:.2f}",
            "currency": tx.currency.upper(),
            "order_description": kwargs.get("description", f"Shopnoltd deposit {reference}"),
            "success_url": return_url or f"{settings.base_callback_url}/checkout/success?ref={reference}",
            "cancel_url": kwargs.get("cancel_url", f"{settings.base_callback_url}/checkout/cancel?ref={reference}"),
            "fail_url": kwargs.get("fail_url", f"{settings.base_callback_url}/checkout/failure?ref={reference}"),
            "ipn_url": kwargs.get("ipn_url", f"{settings.base_callback_url}/webhook/moneybag"),
            "customer": {
                "name": kwargs.get("customer_name", "Shopnoltd Customer"),
                "email": kwargs.get("customer_email"),
                "phone": kwargs.get("customer_phone"),
                "country": kwargs.get("customer_country", "Bangladesh"),
            },
        }
        payload["customer"] = {k: v for k, v in payload["customer"].items() if v is not None}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/api/v2/payments/checkout",
                headers={
                    "Content-Type": "application/json",
                    "X-Merchant-API-Key": settings.moneybag_api_key,
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        data = body.get("data") or {}
        if isinstance(data, list):
            data = data[0] if data else {}
        return {
            "external_id": data.get("transaction_id") or data.get("session_id") or reference,
            "session_id": data.get("session_id"),
            "transaction_id": data.get("transaction_id"),
            "status": "pending",
            "redirect_url": data.get("checkout_url") or data.get("redirect_url"),
            "is_demo": False,
            "raw_response": body,
        }

    async def create_withdrawal(self, tx, **kwargs):
        raise NotImplementedError("Moneybag is checkout/deposit-only in this integration")

    async def verify_webhook(self, request_body: bytes, headers: dict) -> dict:
        secret = settings.moneybag_webhook_secret
        if not secret:
            raise ValueError("moneybag_webhook_secret is not configured")
        timestamp = headers.get("x-webhook-timestamp") or headers.get("X-Webhook-Timestamp")
        signature = headers.get("x-webhook-signature") or headers.get("X-Webhook-Signature")
        if not timestamp or not signature:
            raise ValueError("missing Moneybag webhook signature headers")
        ts = int(timestamp)
        if abs(int(time.time()) - ts) > settings.moneybag_webhook_tolerance_seconds:
            raise ValueError("stale Moneybag webhook")
        signed = f"{timestamp}.".encode() + request_body
        digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, f"sha256={digest}"):
            raise ValueError("invalid Moneybag webhook signature")
        body = json.loads(request_body.decode("utf-8"))
        event_type = headers.get("x-webhook-event-type") or headers.get("X-Webhook-Event-Type")
        data = body.get("data") or body
        if isinstance(data, list):
            data = data[0] if data else {}
        status = {
            "payment.success": "SUCCESS",
            "payment.failed": "FAILED",
            "payment.cancelled": "CANCELLED",
        }.get(event_type or body.get("event_type"), str(data.get("status", "")).upper())
        return {
            "external_id": data.get("transaction_id") or data.get("payment_transaction_id") or data.get("order_id"),
            "status": status,
            "event_id": headers.get("x-webhook-event-id") or headers.get("X-Webhook-Event-Id"),
            "data": data,
        }

    async def get_status(self, external_id: str):
        if not self.enabled:
            return "demo"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.base_url}/api/v2/payments/verify/{external_id}",
                headers={"X-Merchant-API-Key": settings.moneybag_api_key},
            )
            response.raise_for_status()
            body = response.json()
        data = body.get("data") or body
        if isinstance(data, list):
            data = data[0] if data else {}
        return str(data.get("status") or data.get("payment_status") or "unknown").lower()
