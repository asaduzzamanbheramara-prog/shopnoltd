"""Billing integration for domain registration.

Domain charges use the payment-service wallet/transaction system and a
stable idempotency key so retries cannot charge the same domain order twice.
"""

from decimal import Decimal
import hashlib

import httpx


class InsufficientFundsError(RuntimeError):
    """The payment service rejected a transfer for insufficient available funds."""


class IdempotencyConflictError(RuntimeError):
    """The same idempotency key was reused with a different transfer payload."""


class BillingService:
    def __init__(self, payment_service_url: str, platform_wallet_user_id: str, timeout: int = 10):
        self.payment_service_url = payment_service_url.rstrip("/")
        self.platform_wallet_user_id = platform_wallet_user_id
        self.timeout = timeout

    @staticmethod
    def _idempotency_key(user_id: str, operation: str, request_key: str) -> str:
        """Scope retries to one user's explicit operation key."""
        raw = f"domain:{user_id}:{operation}:{request_key.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def check_wallet_balance(self, user_token: str, currency: str, required_amount: Decimal) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            resp = await c.get(
                f"{self.payment_service_url}/api/v1/wallets/{currency.upper()}",
                headers={"Authorization": f"Bearer {user_token}"},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"payment-service wallet check failed: {resp.text}")
            data = resp.json()
            balance = Decimal(str(data.get("balance", 0)))
            return {"balance": balance, "sufficient": balance >= required_amount}

    async def charge_for_domain(
        self,
        user_token: str,
        currency: str,
        amount: Decimal,
        domain: str,
        years: int,
        *,
        user_id: str,
        operation: str,
        request_key: str,
    ) -> dict:
        key = self._idempotency_key(user_id, operation, request_key)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                resp = await c.post(
                    f"{self.payment_service_url}/api/v1/transfers",
                    headers={"Authorization": f"Bearer {user_token}"},
                    json={
                        "to_user_id": self.platform_wallet_user_id,
                        "currency": currency.upper(),
                        "amount": str(amount),
                        "note": f"Domain {operation}: {domain} ({years}yr)",
                        "idempotency_key": key,
                    },
                )
        except httpx.HTTPError as exc:
            raise RuntimeError(
                "Payment service response was not confirmed; retry with the same idempotency key"
            ) from exc
        if resp.status_code == 400:
            try:
                detail = resp.json().get("detail")
            except (ValueError, AttributeError):
                detail = None
            if detail == "insufficient available funds":
                raise InsufficientFundsError()
        if resp.status_code == 409:
            raise IdempotencyConflictError()
        if resp.status_code not in (200, 201):
            raise RuntimeError("Payment service could not confirm the domain charge")
        return resp.json()
