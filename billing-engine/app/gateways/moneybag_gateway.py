"""Moneybag hosted-checkout gateway.

Moneybag's current reviewed sandbox contract is server-to-server JSON:
POST /api/v2/payments/checkout and GET /api/v2/payments/verify/{transaction_id}.
Webhook signatures are HMAC-SHA256 over ``timestamp.raw_body``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import requests

from app import config
from app.gateways.base import GatewayResult, PaymentGateway


BASE_URLS = {
    "sandbox": "https://sandbox.api.moneybag.com.bd",
    "live": "https://api.moneybag.com.bd",
}


class MoneybagGateway(PaymentGateway):
    name = "moneybag"

    def __init__(self):
        self.api_key = config.MONEYBAG_API_KEY
        self.webhook_secret = config.MONEYBAG_WEBHOOK_SECRET
        self.mode = config.MONEYBAG_MODE
        self.base_url = BASE_URLS.get(self.mode, BASE_URLS["sandbox"])
        self.enabled = bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Merchant-API-Key": self.api_key,
        }

    def create_payment(self, amount: float, currency: str, reference: str, **kwargs) -> dict[str, Any]:
        if not self.enabled:
            return GatewayResult(
                gateway=self.name,
                is_demo=True,
                status="pending",
                redirect_url=None,
                gateway_reference=None,
                note="Moneybag is not configured; no payment was sent.",
            )

        currency = currency.upper()
        payload = {
            "order_id": reference,
            "order_amount": f"{amount:.2f}",
            "currency": currency,
            "order_description": kwargs.get("description", f"Shopnoltd order {reference}"),
            "success_url": kwargs.get("success_url", f"{config.BASE_CALLBACK_URL}/checkout/success?ref={reference}"),
            "cancel_url": kwargs.get("cancel_url", f"{config.BASE_CALLBACK_URL}/checkout/cancel?ref={reference}"),
            "fail_url": kwargs.get("fail_url", f"{config.BASE_CALLBACK_URL}/checkout/failure?ref={reference}"),
            "ipn_url": kwargs.get("ipn_url", f"{config.BASE_CALLBACK_URL}/webhook/moneybag/ipn"),
            "customer": {
                "name": kwargs.get("customer_name") or "Shopnoltd Customer",
                "email": kwargs.get("customer_email"),
                "phone": kwargs.get("customer_phone"),
                "address": kwargs.get("customer_address"),
                "city": kwargs.get("customer_city", "Dhaka"),
                "postcode": kwargs.get("customer_postcode"),
                "country": kwargs.get("customer_country", "Bangladesh"),
            },
        }
        payload["customer"] = {k: v for k, v in payload["customer"].items() if v is not None}

        response = requests.post(
            f"{self.base_url}/api/v2/payments/checkout",
            headers=self._headers(),
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") or {}
        if isinstance(data, list):
            data = data[0] if data else {}

        checkout_url = data.get("checkout_url") or data.get("redirect_url")
        session_id = data.get("session_id")
        transaction_id = data.get("transaction_id")
        gateway_reference = transaction_id or session_id or reference

        return GatewayResult(
            gateway=self.name,
            is_demo=False,
            status="pending",
            redirect_url=checkout_url,
            gateway_reference=gateway_reference,
            session_id=session_id,
            transaction_id=transaction_id,
            expires_at=data.get("expires_at"),
            raw_response=body,
        )

    def verify_webhook(self, payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
        if not self.webhook_secret:
            raise ValueError("MONEYBAG_WEBHOOK_SECRET is not configured")

        timestamp = headers.get("x-webhook-timestamp") or headers.get("X-Webhook-Timestamp")
        signature = headers.get("x-webhook-signature") or headers.get("X-Webhook-Signature")
        event_id = headers.get("x-webhook-event-id") or headers.get("X-Webhook-Event-Id")
        event_type = headers.get("x-webhook-event-type") or headers.get("X-Webhook-Event-Type")
        if not timestamp or not signature:
            raise ValueError("Missing Moneybag webhook signature headers")

        try:
            ts = int(timestamp)
        except ValueError as exc:
            raise ValueError("Invalid Moneybag webhook timestamp") from exc
        if abs(int(time.time()) - ts) > config.MONEYBAG_WEBHOOK_TOLERANCE_SECONDS:
            raise ValueError("Stale Moneybag webhook")

        signed = f"{timestamp}.".encode() + payload
        digest = hmac.new(self.webhook_secret.encode(), signed, hashlib.sha256).hexdigest()
        expected = f"sha256={digest}"
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid Moneybag webhook signature")

        body = json.loads(payload.decode("utf-8"))
        data = body.get("data") or body
        if isinstance(data, list):
            data = data[0] if data else {}
        status_map = {
            "payment.success": "completed",
            "payment.failed": "failed",
            "payment.cancelled": "cancelled",
        }
        status = status_map.get(event_type or body.get("event_type"), body.get("status", "pending"))
        gateway_reference = (
            data.get("transaction_id")
            or data.get("payment_transaction_id")
            or data.get("order_id")
            or body.get("transaction_id")
            or body.get("order_id")
        )
        return {
            "gateway_reference": gateway_reference,
            "status": status,
            "amount": data.get("amount") or data.get("order_amount"),
            "currency": data.get("currency"),
            "event_id": event_id,
            "event_type": event_type,
            "raw": body,
        }

    def get_status(self, external_id: str) -> str:
        if not self.enabled:
            return "demo"
        response = requests.get(
            f"{self.base_url}/api/v2/payments/verify/{external_id}",
            headers={"X-Merchant-API-Key": self.api_key},
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data") or body
        if isinstance(data, list):
            data = data[0] if data else {}
        return str(data.get("status") or data.get("payment_status") or "unknown").lower()
