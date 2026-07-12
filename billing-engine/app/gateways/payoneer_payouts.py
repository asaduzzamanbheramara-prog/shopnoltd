"""
Payoneer integration - PAYOUTS ONLY.

Payoneer does not offer a customer-facing "pay with Payoneer" checkout button
through its public API; it's built for paying money out (marketplace seller
payouts, affiliate/freelancer payments, mass payouts). If Shopnoltd needs to
pay suppliers, affiliates, or marketplace sellers, this is the real fit.
If what's actually wanted is "let a customer pay their order with Payoneer",
that isn't something Payoneer's API supports - Stripe/PayPal/crypto cover the
"customer pays us" side already.
"""
import requests
from app import config

BASE_URLS = {
    True: "https://api.sandbox.payoneer.com/v2",
    False: "https://api.payoneer.com/v2",
}


class PayoneerPayouts:
    name = "payoneer"

    def __init__(self):
        self.enabled = config.PAYONEER_ENABLED
        self.base_url = BASE_URLS[config.PAYONEER_SANDBOX]

    def send_payout(self, payee_id: str, amount: float, currency: str, description: str) -> dict:
        if not self.enabled:
            return {
                "gateway": self.name, "is_demo": True, "status": "pending",
                "note": "Payoneer not configured (missing program id / API credentials) - running in demo mode.",
            }
        resp = requests.post(
            f"{self.base_url}/programs/{config.PAYONEER_PROGRAM_ID}/payouts",
            auth=(config.PAYONEER_API_USERNAME, config.PAYONEER_API_PASSWORD),
            json={
                "payee_id": payee_id,
                "amount": f"{amount:.2f}",
                "currency": currency.upper(),
                "description": description,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"gateway": self.name, "is_demo": False, "status": data.get("status", "submitted"), "raw": data}
