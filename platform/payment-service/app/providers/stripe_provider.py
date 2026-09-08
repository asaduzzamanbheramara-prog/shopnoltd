from decimal import Decimal, ROUND_DOWN

import stripe
from app.core.config import settings
from app.providers.base import BaseProvider

stripe.api_key = settings.stripe_secret_key


class StripeProvider(BaseProvider):
    def __init__(self):
        super().__init__("stripe")
        self.enabled = bool(settings.stripe_secret_key)

    async def create_deposit(self, tx, return_url=None, **kwargs):
        if not self.enabled:
            raise RuntimeError("Stripe credentials are not configured")
        minor_units = int(
            (Decimal(str(tx.amount)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_DOWN)
        )
        intent = stripe.PaymentIntent.create(
            amount=minor_units,
            currency=tx.currency.lower(),
            metadata={"tx_id": str(tx.id), "tenant_id": tx.tenant_id},
            automatic_payment_methods={"enabled": True},
        )
        return {
            "external_id": intent.id,
            "client_secret": intent.client_secret,
            "redirect_url": return_url,
        }

    async def create_withdrawal(self, tx, destination, **kwargs):
        if not self.enabled:
            raise RuntimeError("Stripe credentials are not configured")
        minor_units = int(
            (Decimal(str(tx.amount)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_DOWN)
        )
        tr = stripe.Transfer.create(
            amount=minor_units, currency=tx.currency.lower(), destination=destination
        )
        return {"external_id": tr.id, "status": tr.status}

    async def verify_webhook(self, body, headers):
        event = stripe.Webhook.construct_event(
            body, headers.get("stripe-signature", ""), settings.stripe_webhook_secret
        )
        return event.to_dict()

    async def get_status(self, external_id):
        if not self.enabled:
            return "unavailable"
        intent = stripe.PaymentIntent.retrieve(external_id)
        return intent.status
