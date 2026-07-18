import hashlib
import hmac
import json
import time

import httpx
from app.core.config import settings
from app.providers.base import BaseProvider


class BinancePayProvider(BaseProvider):
    BASE = "https://bpay.binanceapi.com"

    def __init__(self):
        super().__init__("binance")

    def _sign(self, params):
        payload = json.dumps(params, separators=(",", ":"), sort_keys=True)
        ts = int(time.time() * 1000)
        nonce = str(ts)
        body = f"{ts}\n{nonce}\n{payload}\n"
        sig = hmac.new(
            settings.binance_pay_secret.encode(), body.encode(), hashlib.sha512
        ).hexdigest()
        return ts, nonce, sig

    async def create_deposit(self, tx, return_url=None, **kwargs):
        params = {
            "env": {"terminalType": "WEB"},
            "orderAmount": float(tx.amount),
            "currency": tx.currency.upper(),
            "goods": {"goodsName": f"Shopnoltd deposit {tx.id}", "goodsCategory": "1000"},
            "orderId": str(tx.id),
            "returnUrl": return_url or "https://shopnoltd.dpdns.org",
            "webhookUrl": "https://api.shopnoltd.dpdns.org/api/v1/webhooks/binance",
        }
        ts, nonce, sig = self._sign(params)
        headers = {
            "content-type": "application/json",
            "BinancePay-Timestamp": str(ts),
            "BinancePay-Nonce": nonce,
            "BinancePay-Signature": sig,
        }
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{self.BASE}/binancepay/openapi/v2/order", json=params, headers=headers, timeout=20
            )
        r.raise_for_status()
        d = r.json()["data"]
        return {
            "external_id": d["prepayId"],
            "qr_code": d["qrCodeLink"],
            "checkout_url": d.get("universalUrl"),
            "redirect_url": d.get("universalUrl"),
        }

    async def create_withdrawal(self, tx, destination, **kwargs):
        raise NotImplementedError(
            "Binance Pay payouts via Binance API; use manual withdrawal with admin approval"
        )

    async def verify_webhook(self, body, headers):
        ts = headers.get("BinancePay-Timestamp")
        nonce = headers.get("BinancePay-Nonce")
        sig = headers.get("BinancePay-Signature")
        if not (ts and nonce and sig):
            raise ValueError("missing headers")
        expected = hmac.new(
            settings.binance_pay_secret.encode(),
            f"{ts}\n{nonce}\n{body.decode()}\n".encode(),
            hashlib.sha512,
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise ValueError("bad signature")
        return json.loads(body)

    async def get_status(self, external_id):
        params = {"prepayId": external_id}
        ts, nonce, sig = self._sign(params)
        headers = {
            "content-type": "application/json",
            "BinancePay-Timestamp": str(ts),
            "BinancePay-Nonce": nonce,
            "BinancePay-Signature": sig,
        }
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{self.BASE}/binancepay/openapi/v2/query", json=params, headers=headers, timeout=20
            )
        r.raise_for_status()
        return r.json()["data"]["status"]
