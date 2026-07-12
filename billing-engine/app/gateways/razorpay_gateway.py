import hmac
import hashlib
import json
import uuid
from app import config
from app.gateways.base import PaymentGateway, GatewayResult

try:
    import razorpay
except ImportError:
    razorpay = None


class RazorpayGateway(PaymentGateway):
    name = "razorpay"

    def __init__(self):
        self.enabled = config.RAZORPAY_ENABLED and razorpay is not None
        self.client = (
            razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))
            if self.enabled else None
        )

    def create_payment(self, amount: float, currency: str, reference: str, **kwargs) -> GatewayResult:
        if not self.enabled:
            return GatewayResult(
                gateway=self.name, is_demo=True, status="pending",
                gateway_reference=f"demo_order_{uuid.uuid4().hex[:12]}",
                redirect_url=None,
                note="Razorpay not configured (missing key id/secret) - running in demo mode.",
            )
        order = self.client.order.create({
            "amount": int(round(amount * 100)),
            "currency": currency.upper(),
            "receipt": reference,
            "payment_capture": 1,
        })
        return GatewayResult(
            gateway=self.name, is_demo=False, status="pending",
            gateway_reference=order["id"], redirect_url=None,
            # Razorpay uses client-side Checkout.js with this order_id rather than a hosted redirect URL.
            raw=order,
        )

    def verify_webhook(self, payload: bytes, headers: dict) -> dict:
        if not self.enabled:
            raise RuntimeError("Razorpay not configured")
        signature = headers.get("x-razorpay-signature")
        expected = hmac.new(
            config.RAZORPAY_KEY_SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature or ""):
            raise ValueError("Invalid Razorpay webhook signature")
        event = json.loads(payload)
        entity = event["payload"]["payment"]["entity"]
        return {
            "gateway": self.name,
            "gateway_reference": entity.get("order_id"),
            "status": "completed" if entity.get("status") == "captured" else entity.get("status"),
            "amount": (entity.get("amount") or 0) / 100,
            "currency": entity.get("currency"),
            "reference": entity.get("notes", {}).get("reference"),
        }
