import uuid

import requests

from app import config
from app.gateways.base import GatewayResult, PaymentGateway

BASE_URLS = {
    True: "https://tokenized.sandbox.bka.sh/v1.2.0-beta",
    False: "https://tokenized.pay.bka.sh/v1.2.0-beta",
}


class BkashGateway(PaymentGateway):
    name = "bkash"

    def __init__(self):
        self.enabled = config.BKASH_ENABLED
        self.sandbox = config.BKASH_SANDBOX
        self.base_url = BASE_URLS[self.sandbox]
        self._token = None

    def _headers(self, with_token=True) -> dict:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "username": config.BKASH_USERNAME,
            "password": config.BKASH_PASSWORD,
        }
        if with_token and self._token:
            h["Authorization"] = self._token
        return h

    def _grant_token(self) -> str:
        resp = requests.post(
            f"{self.base_url}/tokenized/checkout/token/grant",
            headers=self._headers(with_token=False),
            json={"app_key": config.BKASH_APP_KEY, "app_secret": config.BKASH_APP_SECRET},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["id_token"]
        return self._token

    def create_payment(
        self, amount: float, currency: str, reference: str, **kwargs
    ) -> GatewayResult:
        if not self.enabled:
            return GatewayResult(
                gateway=self.name,
                is_demo=True,
                status="pending",
                gateway_reference=f"demo_bkash_{uuid.uuid4().hex[:12]}",
                redirect_url=None,
                note="bKash not configured (missing app key/secret/username/password) - running in demo mode.",
            )
        if currency.upper() != "BDT":
            raise ValueError("bKash only supports BDT")
        self._grant_token()
        resp = requests.post(
            f"{self.base_url}/tokenized/checkout/create",
            headers={**self._headers(), "X-App-Key": config.BKASH_APP_KEY},
            json={
                "mode": "0011",
                "payerReference": reference,
                "callbackURL": f"{config.BASE_CALLBACK_URL}/webhook/bkash/callback",
                "amount": f"{amount:.2f}",
                "currency": "BDT",
                "intent": "sale",
                "merchantInvoiceNumber": reference,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return GatewayResult(
            gateway=self.name,
            is_demo=False,
            status="pending",
            gateway_reference=data.get("paymentID"),
            redirect_url=data.get("bkashURL"),
            raw=data,
        )

    def execute_payment(self, payment_id: str) -> dict:
        self._grant_token()
        resp = requests.post(
            f"{self.base_url}/tokenized/checkout/execute",
            headers={**self._headers(), "X-App-Key": config.BKASH_APP_KEY},
            json={"paymentID": payment_id},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def verify_webhook(self, payload: bytes, headers: dict) -> dict:
        # bKash uses a redirect callback with paymentID + status query params, then requires the
        # server to call execute_payment() to finalize. Handled in main.py `/webhook/bkash/callback`.
        raise NotImplementedError
