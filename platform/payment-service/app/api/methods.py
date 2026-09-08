"""Payment methods / gateways introspection.

Mount this at prefix="/api/v1/billing" in main.py so it serves
GET /api/v1/billing/gateways — the exact path financialApi.js already
calls. This replaces the frontend's hardcoded `<option value="stripe">`
fallback with the real, live state of every configured provider.

`live` = credentials are configured AND the provider isn't in sandbox
mode (for providers that have a sandbox flag). Manual/crypto methods
need no external credentials, so they're always reported live.
"""

from app.core.config import settings
from app.models.models import PaymentMethod
from fastapi import APIRouter

router = APIRouter()

_METHOD_CONFIG = {
    PaymentMethod.stripe: (lambda s: bool(s.stripe_secret_key), None),
    PaymentMethod.paypal: (
        lambda s: bool(s.paypal_client_id and s.paypal_secret),
        lambda s: s.paypal_mode == "sandbox",
    ),
    PaymentMethod.binance: (lambda s: bool(s.binance_pay_key and s.binance_pay_secret), None),
    PaymentMethod.payeer: (lambda s: bool(s.payeer_account and s.payeer_api_key), None),
    PaymentMethod.bkash: (lambda s: bool(s.bkash_app_key and s.bkash_app_secret), None),
    PaymentMethod.nagad: (
        lambda s: bool(s.nagad_merchant_id and s.nagad_merchant_key),
        lambda s: s.nagad_sandbox,
    ),
    PaymentMethod.rocket: (lambda s: bool(s.rocket_merchant_id and s.rocket_merchant_key), None),
    PaymentMethod.bank: (lambda s: True, None),
    PaymentMethod.manual: (lambda s: True, None),
    PaymentMethod.btc: (lambda s: True, None),
    PaymentMethod.eth: (lambda s: True, None),
    PaymentMethod.usdt: (lambda s: True, None),
    PaymentMethod.bnb: (lambda s: True, None),
    PaymentMethod.sol: (lambda s: True, None),
    PaymentMethod.trx: (lambda s: True, None),
    PaymentMethod.razorpay: (lambda s: bool(s.razorpay_key_id and s.razorpay_key_secret), None),
    PaymentMethod.sslcommerz: (
        lambda s: bool(s.sslcommerz_store_id and s.sslcommerz_store_password),
        lambda s: s.sslcommerz_sandbox,
    ),
    PaymentMethod.payoneer: (
        lambda s: bool(s.payoneer_program_id and s.payoneer_api_username),
        lambda s: s.payoneer_sandbox,
    ),
}

_DISPLAY_NAMES = {
    PaymentMethod.stripe: "Stripe (card)",
    PaymentMethod.paypal: "PayPal",
    PaymentMethod.binance: "Binance Pay",
    PaymentMethod.payeer: "Payeer",
    PaymentMethod.bkash: "bKash",
    PaymentMethod.nagad: "Nagad",
    PaymentMethod.rocket: "Rocket",
    PaymentMethod.bank: "Bank transfer (manual)",
    PaymentMethod.manual: "Manual / admin-approved",
    PaymentMethod.btc: "Bitcoin",
    PaymentMethod.eth: "Ethereum",
    PaymentMethod.usdt: "USDT",
    PaymentMethod.bnb: "BNB",
    PaymentMethod.sol: "Solana",
    PaymentMethod.trx: "Tron",
    PaymentMethod.razorpay: "Razorpay",
    PaymentMethod.sslcommerz: "SSLCommerz",
    PaymentMethod.payoneer: "Payoneer (payout)",
}


@router.get("/gateways")
async def list_gateways():
    gateways = []
    for method, (configured_fn, sandbox_fn) in _METHOD_CONFIG.items():
        configured = configured_fn(settings)
        sandbox = sandbox_fn(settings) if sandbox_fn else False
        gateways.append(
            {
                "name": method.value,
                "display_name": _DISPLAY_NAMES.get(method, method.value),
                "credentials_configured": configured,
                "live": configured and not sandbox,
            }
        )
    return {"gateways": gateways}
