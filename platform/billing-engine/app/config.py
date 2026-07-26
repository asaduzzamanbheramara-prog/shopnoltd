"""
Central configuration for the Shopnoltd billing engine.

Every payment gateway is configured purely from environment variables
(populated in production via a Kubernetes Secret, e.g. `stripe-secret`,
`bkash-secret`, etc.). A gateway automatically runs in DEMO MODE if its
required credentials are missing, so the API always tells the truth about
whether a given payment is real or simulated -- it never fakes a "success
rate" the way the old prototype did.
"""

import os

from dotenv import load_dotenv

load_dotenv()  # reads .env for local dev; in Docker/K8s, real env vars take priority and this is a harmless no-op


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


DATABASE_URL = _env("DATABASE_URL", "sqlite:///./billing.db")

# ---------------------------------------------------------------------------
# Internal service auth (protects /wallet/deduct, /wallet/fine, /wallet/adjust)
# ---------------------------------------------------------------------------
INTERNAL_API_KEY = _env("INTERNAL_API_KEY")

# ---------------------------------------------------------------------------
# Stripe (cards, wallets - global)
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY = _env("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = _env("STRIPE_WEBHOOK_SECRET")
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY)

# ---------------------------------------------------------------------------
# PayPal (global)
# ---------------------------------------------------------------------------
PAYPAL_CLIENT_ID = _env("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = _env("PAYPAL_CLIENT_SECRET")
PAYPAL_MODE = _env("PAYPAL_MODE", "sandbox")  # "sandbox" or "live"
PAYPAL_ENABLED = bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)

# ---------------------------------------------------------------------------
# Razorpay (India, also usable for BDT via INR corridor)
# ---------------------------------------------------------------------------
RAZORPAY_KEY_ID = _env("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = _env("RAZORPAY_KEY_SECRET")
RAZORPAY_ENABLED = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)

# ---------------------------------------------------------------------------
# SSLCommerz (Bangladesh - cards, mobile banking, net banking aggregator)
# ---------------------------------------------------------------------------
SSLCOMMERZ_STORE_ID = _env("SSLCOMMERZ_STORE_ID")
SSLCOMMERZ_STORE_PASSWORD = _env("SSLCOMMERZ_STORE_PASSWORD")
SSLCOMMERZ_SANDBOX = _env("SSLCOMMERZ_SANDBOX", "true").lower() != "false"
SSLCOMMERZ_ENABLED = bool(SSLCOMMERZ_STORE_ID and SSLCOMMERZ_STORE_PASSWORD)

# ---------------------------------------------------------------------------
# bKash (Bangladesh mobile wallet - Tokenized Checkout API)
# ---------------------------------------------------------------------------
BKASH_APP_KEY = _env("BKASH_APP_KEY")
BKASH_APP_SECRET = _env("BKASH_APP_SECRET")
BKASH_USERNAME = _env("BKASH_USERNAME")
BKASH_PASSWORD = _env("BKASH_PASSWORD")
BKASH_SANDBOX = _env("BKASH_SANDBOX", "true").lower() != "false"
BKASH_ENABLED = bool(BKASH_APP_KEY and BKASH_APP_SECRET and BKASH_USERNAME and BKASH_PASSWORD)

# ---------------------------------------------------------------------------
# Nagad (Bangladesh mobile wallet - Merchant API, RSA signed)
# ---------------------------------------------------------------------------
NAGAD_MERCHANT_ID = _env("NAGAD_MERCHANT_ID")
NAGAD_MERCHANT_PRIVATE_KEY = _env("NAGAD_MERCHANT_PRIVATE_KEY")  # PEM string
NAGAD_PG_PUBLIC_KEY = _env("NAGAD_PG_PUBLIC_KEY")  # PEM string, provided by Nagad
NAGAD_SANDBOX = _env("NAGAD_SANDBOX", "true").lower() != "false"
NAGAD_ENABLED = bool(NAGAD_MERCHANT_ID and NAGAD_MERCHANT_PRIVATE_KEY and NAGAD_PG_PUBLIC_KEY)

# ---------------------------------------------------------------------------
# Crypto (Bitcoin + ~200 other coins) via NOWPayments
# Chosen over building raw blockchain nodes/wallets yourself: NOWPayments is a
# non-custodial payment processor - coins settle straight to your own wallet
# address, they just handle the invoice/webhook plumbing.
# ---------------------------------------------------------------------------
NOWPAYMENTS_API_KEY = _env("NOWPAYMENTS_API_KEY")
NOWPAYMENTS_IPN_SECRET = _env("NOWPAYMENTS_IPN_SECRET")
NOWPAYMENTS_SANDBOX = _env("NOWPAYMENTS_SANDBOX", "true").lower() != "false"
CRYPTO_ENABLED = bool(NOWPAYMENTS_API_KEY)

# ---------------------------------------------------------------------------
# Payoneer - PAYOUTS only (paying suppliers/affiliates/sellers), not a
# customer-facing checkout gateway. Payoneer's public API doesn't offer a
# "pay with Payoneer" checkout button; it's for sending money out.
# ---------------------------------------------------------------------------
PAYONEER_PROGRAM_ID = _env("PAYONEER_PROGRAM_ID")
PAYONEER_API_USERNAME = _env("PAYONEER_API_USERNAME")
PAYONEER_API_PASSWORD = _env("PAYONEER_API_PASSWORD")
PAYONEER_SANDBOX = _env("PAYONEER_SANDBOX", "true").lower() != "false"
PAYONEER_ENABLED = bool(PAYONEER_PROGRAM_ID and PAYONEER_API_USERNAME and PAYONEER_API_PASSWORD)

# ---------------------------------------------------------------------------
# Live exchange rates
# ---------------------------------------------------------------------------
EXCHANGE_RATE_API_KEY = _env(
    "EXCHANGE_RATE_API_KEY"
)  # exchangerate.host / openexchangerates.org key
EXCHANGE_RATE_LIVE_ENABLED = bool(EXCHANGE_RATE_API_KEY)
EXCHANGE_RATE_CACHE_SECONDS = int(_env("EXCHANGE_RATE_CACHE_SECONDS", "3600"))

BASE_CALLBACK_URL = _env("BASE_CALLBACK_URL", "https://billing.shopnoltd.dpdns.org")

GATEWAY_STATUS = {
    "stripe": STRIPE_ENABLED,
    "paypal": PAYPAL_ENABLED,
    "razorpay": RAZORPAY_ENABLED,
    "sslcommerz": SSLCOMMERZ_ENABLED,
    "bkash": BKASH_ENABLED,
    "nagad": NAGAD_ENABLED,
    "crypto": CRYPTO_ENABLED,
}
