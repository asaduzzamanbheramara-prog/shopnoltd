import uuid

from app import config
from app.gateways.base import GatewayResult, PaymentGateway

try:
    import stripe
except ImportError:
    stripe = None


class StripeGateway(PaymentGateway):
    name = "stripe"

    def __init__(self):
        self.enabled = config.STRIPE_ENABLED and stripe is not None
        if self.enabled:
            stripe.api_key = config.STRIPE_SECRET_KEY

    def create_payment(
        self, amount: float, currency: str, reference: str, **kwargs
    ) -> GatewayResult:
        if not self.enabled:
            return GatewayResult(
                gateway=self.name,
                is_demo=True,
                status="pending",
                gateway_reference=f"demo_cs_{uuid.uuid4().hex[:12]}",
                redirect_url=None,
                note="Stripe not configured (missing STRIPE_SECRET_KEY) - running in demo mode.",
            )
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": currency.lower(),
                        "product_data": {"name": f"Shopnoltd order {reference}"},
                        "unit_amount": int(round(amount * 100)),
                    },
                    "quantity": 1,
                }
            ],
            success_url=kwargs.get(
                "success_url", f"{config.BASE_CALLBACK_URL}/checkout/success?ref={reference}"
            ),
            cancel_url=kwargs.get(
                "cancel_url", f"{config.BASE_CALLBACK_URL}/checkout/cancel?ref={reference}"
            ),
            client_reference_id=reference,
        )
        return GatewayResult(
            gateway=self.name,
            is_demo=False,
            status="pending",
            gateway_reference=session.id,
            redirect_url=session.url,
        )

    def verify_webhook(self, payload: bytes, headers: dict) -> dict:
        if not self.enabled:
            raise RuntimeError("Stripe not configured")
        sig_header = headers.get("stripe-signature") or headers.get("Stripe-Signature")
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=config.STRIPE_WEBHOOK_SECRET,
        )
        obj = event["data"]["object"]
        paid = event["type"] == "checkout.session.completed" and obj.get("payment_status") == "paid"
        return {
            "gateway": self.name,
            "gateway_reference": obj.get("id"),
            "status": "completed" if paid else event["type"],
            "amount": (obj.get("amount_total") or 0) / 100,
            "currency": (obj.get("currency") or "usd").upper(),
            "reference": obj.get("client_reference_id"),
        }
