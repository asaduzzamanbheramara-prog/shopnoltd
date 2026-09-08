"""Billing integration for domain registration.

Rewritten to call payment-service directly (the service with the actual,
working Wallet/Transaction implementation — see the financial-system-fix
patch set from earlier in this thread) instead of billing-engine, whose
wallet API shape was never confirmed to match what this code expected
(`/api/v1/wallet/{user_id}/balance` and `/deduct` — billing-engine and
payment-service are still an unresolved duplication in this project; see
project notes). If billing-engine is actually the intended system of
record instead, this needs to point there and this comment should be
updated — flagging that decision rather than guessing silently.

Debiting reuses payment-service's existing POST /api/v1/transfers
endpoint by forwarding the *user's own* bearer token (transfers requires
the caller's own JWT — it debits `sub`'s wallet, so there's no separate
service-to-service credential to manage). The domain purchase amount is
transferred from the user's wallet to a reserved "platform revenue"
account. Set PLATFORM_WALLET_USER_ID (below, sourced from config) to a
real Keycloak subject id you control before using this in production.
"""

from decimal import Decimal

import httpx


class BillingService:
    def __init__(self, payment_service_url: str, platform_wallet_user_id: str, timeout: int = 10):
        self.payment_service_url = payment_service_url.rstrip("/")
        self.platform_wallet_user_id = platform_wallet_user_id
        self.timeout = timeout

    async def check_wallet_balance(self, user_token: str, currency: str, required_amount: Decimal) -> dict:
        """Check the requesting user's wallet balance (auto-provisions a
        zero-balance wallet if they've never held this currency, same as
        the wallets.py fix — so this never 404s, it just reports insufficient
        funds for a currency the user hasn't funded yet)."""
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
        self, user_token: str, currency: str, amount: Decimal, domain: str, years: int
    ) -> dict:
        """Debit the user's wallet for a domain purchase via an internal
        transfer to the platform revenue wallet. Raises on insufficient
        funds or any transfer failure — caller must NOT proceed with the
        registrar call unless this succeeds."""
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            resp = await c.post(
                f"{self.payment_service_url}/api/v1/transfers",
                headers={"Authorization": f"Bearer {user_token}"},
                json={
                    "to_user_id": self.platform_wallet_user_id,
                    "currency": currency.upper(),
                    "amount": str(amount),
                    "note": f"Domain registration: {domain} ({years}yr)",
                },
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Domain charge failed: {resp.text}")
            return resp.json()
