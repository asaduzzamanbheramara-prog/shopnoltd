"""Canonical financial gateway, capability, and currency metadata.

This registry describes what an integration can do. Runtime credential and
administrator activation state is reported separately by billing-engine.
Unsupported operations are never represented as successful capabilities.
"""

from copy import deepcopy


GATEWAY_REGISTRY = {
    "stripe": {
        "id": "stripe", "name": "Stripe", "provider": "stripe", "supported": True,
        "integration": "native",
        "capabilities": ["checkout", "webhook", "verification"],
        "currencies": ["USD", "EUR", "GBP", "AUD", "CAD", "SGD", "JPY", "HKD", "NZD", "CHF"],
        "payment_methods": ["card", "google_pay", "apple_pay", "link"],
        "notes": "Google Pay is a Stripe payment method/wallet capability, not a separate processor.",
    },
    "paypal": {
        "id": "paypal", "name": "PayPal", "provider": "paypal", "supported": True,
        "integration": "native",
        "capabilities": ["checkout", "webhook", "verification"],
        "currencies": ["USD", "EUR", "GBP", "AUD", "CAD", "JPY", "HKD", "SGD"],
    },
    "binance": {
        "id": "binance", "name": "Binance Pay", "provider": "binance", "supported": True,
        "integration": "native",
        "capabilities": ["checkout", "webhook", "verification"],
        "currencies": ["USDT", "USDC", "BTC", "ETH", "BNB", "BUSD"],
    },
    "razorpay": {
        "id": "razorpay", "name": "Razorpay", "provider": "razorpay", "supported": True,
        "integration": "native",
        "capabilities": ["checkout", "webhook", "verification"],
        "currencies": ["INR", "USD"],
    },
    "sslcommerz": {
        "id": "sslcommerz", "name": "SSLCommerz", "provider": "sslcommerz", "supported": True,
        "integration": "native",
        "capabilities": ["checkout", "webhook", "verification"], "currencies": ["BDT"],
    },
    "bkash": {
        "id": "bkash", "name": "bKash", "provider": "bkash", "supported": True,
        "integration": "native",
        "capabilities": ["checkout", "webhook", "verification"], "currencies": ["BDT"],
    },
    "nagad": {
        "id": "nagad", "name": "Nagad", "provider": "nagad", "supported": True,
        "integration": "native",
        "capabilities": ["checkout", "webhook", "verification"], "currencies": ["BDT"],
    },
    "moneybag": {
        "id": "moneybag", "name": "Moneybag", "provider": "moneybag", "supported": True,
        "integration": "native",
        "capabilities": ["checkout", "webhook", "verification"], "currencies": ["BDT"],
        "payment_methods": [
            "visa", "mastercard", "amex", "unionpay", "diners_club", "dbbl_nexus",
            "bkash", "nagad", "rocket", "upay", "tap",
        ],
    },
    "crypto": {
        "id": "crypto", "name": "Crypto / NOWPayments", "provider": "crypto", "supported": True,
        "integration": "native",
        "capabilities": ["checkout", "webhook", "verification"],
        "currencies": ["BTC", "ETH", "USDT", "USDC", "BNB", "SOL", "TRX", "LTC", "DOGE", "XRP"],
        "notes": "Provider availability is currency/network dependent; UI must use the live gateway catalog.",
    },
    "payeer": {
        "id": "payeer", "name": "Payeer", "provider": "payeer", "supported": True,
        "integration": "manual",
        "capabilities": ["manual_deposit"],
        "currencies": [],
        "notes": "Manual path retained until a verified native Payeer API adapter is configured.",
    },
    "rocket": {
        "id": "rocket", "name": "Rocket", "provider": "rocket", "supported": True,
        "integration": "manual",
        "capabilities": ["manual_deposit"],
        "currencies": ["BDT"],
        "notes": "Manual path retained; no native API success is claimed.",
    },
}

PAYOUT_PROVIDERS = {
    "payoneer": {
        "id": "payoneer", "name": "Payoneer", "provider": "payoneer",
        "supported": True, "integration": "native",
        "capabilities": ["payout"],
        "currencies": ["USD", "EUR", "GBP", "CAD", "AUD"],
        "notes": "Payout-only integration; not a customer checkout gateway.",
    }
}

CURRENCY_REGISTRY = sorted(
    {currency for gateway in GATEWAY_REGISTRY.values() for currency in gateway["currencies"]}
    | {currency for gateway in PAYOUT_PROVIDERS.values() for currency in gateway["currencies"]}
)


def gateway_catalog() -> dict:
    return {
        "gateways": deepcopy(GATEWAY_REGISTRY),
        "payout_providers": deepcopy(PAYOUT_PROVIDERS),
        "currencies": list(CURRENCY_REGISTRY),
    }
