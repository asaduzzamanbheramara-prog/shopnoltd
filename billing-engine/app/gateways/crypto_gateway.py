import hmac
import hashlib
import json
import uuid
import requests
from app import config
from app.gateways.base import PaymentGateway, GatewayResult

BASE_URL = "https://api.nowpayments.io/v1" if not config.NOWPAYMENTS_SANDBOX else "https://api-sandbox.nowpayments.io/v1"


class CryptoGateway(PaymentGateway):
    """Bitcoin and ~200 other coins via NOWPayments (non-custodial - coins settle to your own wallet)."""
    name = "crypto"

    def __init__(self):
        self.enabled = config.CRYPTO_ENABLED

    def _headers(self):
        return {"x-api-key": config.NOWPAYMENTS_API_KEY, "Content-Type": "application/json"}

    def create_payment(self, amount: float, currency: str, reference: str, **kwargs) -> GatewayResult:
        pay_currency = kwargs.get("crypto_currency", "btc")  # e.g. btc, eth, usdttrc20
        if not self.enabled:
            return GatewayResult(
                gateway=self.name, is_demo=True, status="pending",
                gateway_reference=f"demo_crypto_{uuid.uuid4().hex[:12]}",
                redirect_url=None,
                note="Crypto payments not configured (missing NOWPAYMENTS_API_KEY) - running in demo mode.",
            )
        resp = requests.post(
            f"{BASE_URL}/invoice",
            headers=self._headers(),
            json={
                "price_amount": amount,
                "price_currency": currency.lower(),
                "pay_currency": pay_currency,
                "order_id": reference,
                "ipn_callback_url": f"{config.BASE_CALLBACK_URL}/webhook/crypto",
                "success_url": kwargs.get("success_url", f"{config.BASE_CALLBACK_URL}/checkout/success?ref={reference}"),
                "cancel_url": kwargs.get("cancel_url", f"{config.BASE_CALLBACK_URL}/checkout/cancel?ref={reference}"),
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return GatewayResult(
            gateway=self.name, is_demo=False, status="pending",
            gateway_reference=str(data.get("id")), redirect_url=data.get("invoice_url"),
            raw=data,
        )

    def verify_webhook(self, payload: bytes, headers: dict) -> dict:
        if not self.enabled:
            raise RuntimeError("Crypto gateway not configured")
        sig = headers.get("x-nowpayments-sig")
        # NOWPayments signs a sorted-key JSON representation of the payload
        body = json.loads(payload)
        sorted_body = json.dumps(body, sort_keys=True, separators=(",", ":"))
        expected = hmac.new(config.NOWPAYMENTS_IPN_SECRET.encode(), sorted_body.encode(), hashlib.sha512).hexdigest()
        if not hmac.compare_digest(expected, sig or ""):
            raise ValueError("Invalid NOWPayments IPN signature")
        status = body.get("payment_status")
        return {
            "gateway": self.name,
            "gateway_reference": str(body.get("invoice_id") or body.get("payment_id")),
            "status": "completed" if status == "finished" else status,
            "amount": body.get("price_amount"),
            "currency": (body.get("price_currency") or "").upper(),
            "reference": body.get("order_id"),
        }
