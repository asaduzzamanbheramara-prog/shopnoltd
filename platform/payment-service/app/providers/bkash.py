import json

import httpx
from app.core.config import settings
from app.providers.base import BaseProvider

TOKEN_URL = "https://tokenized.pay.bka.sh/v1.2.0-beta/tokenized/checkout/token/grant"
CREATE_URL = "https://tokenized.pay.bka.sh/v1.2.0-beta/tokenized/checkout/payment/create"
QUERY_URL = "https://tokenized.pay.bka.sh/v1.2.0-beta/tokenized/checkout/payment/query"
EXEC_URL = "https://tokenized.pay.bka.sh/v1.2.0-beta/tokenized/checkout/payment/execute"


class BkashProvider(BaseProvider):
    def __init__(self):
        super().__init__("bkash")
        self._tok = None

    async def _token(self):
        async with httpx.AsyncClient() as c:
            r = await c.post(
                TOKEN_URL,
                json={"app_key": settings.bkash_app_key, "app_secret": settings.bkash_app_secret},
                headers={"username": settings.bkash_app_key, "password": settings.bkash_app_secret},
                timeout=20,
            )
        r.raise_for_status()
        self._tok = r.json()["id_token"]
        return self._tok

    async def create_deposit(self, tx, return_url=None, **kwargs):
        tok = await self._token()
        amount = f"{float(tx.amount):.2f}"
        async with httpx.AsyncClient() as c:
            r = await c.post(
                CREATE_URL,
                json={
                    "mode": "0011",
                    "payerReference": tx.tenant_id,
                    "callbackURL": "https://api.shopnoltd.dpdns.org/api/v1/webhooks/bkash",
                    "amount": amount,
                    "currency": "BDT",
                    "intent": "sale",
                    "merchantInvoiceNumber": str(tx.id),
                },
                headers={"Authorization": tok, "X-APP-Key": settings.bkash_app_key},
                timeout=20,
            )
        r.raise_for_status()
        d = r.json()
        return {
            "external_id": d["paymentID"],
            "redirect_url": d["bkashURL"],
            "approval_url": d["bkashURL"],
        }

    async def create_withdrawal(self, tx, destination, **kwargs):
        raise NotImplementedError("bkash payouts need b2c Payout API; use manual withdrawal")

    async def verify_webhook(self, body, headers):
        payload = json.loads(body)
        payment_id = payload.get("paymentID") or payload.get("paymentId")
        if not payment_id:
            raise RuntimeError("bKash callback is missing paymentID")
        status = await self.get_status(payment_id)
        return {
            "event_id": f"bkash:{payment_id}:{status}",
            "external_id": payment_id,
            "status": status,
            "amount": payload.get("amount"),
            "currency": payload.get("currency") or "BDT",
        }

    async def get_status(self, external_id):
        tok = await self._token()
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(
                f"{QUERY_URL}/{external_id}",
                headers={"Authorization": tok, "X-APP-Key": settings.bkash_app_key},
            )
        r.raise_for_status()
        data = r.json()
        return str(data.get("transactionStatus") or data.get("status") or "PENDING").upper()
