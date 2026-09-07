"""Canonical financial gateway and currency metadata.

This registry describes what Shopnoltd implements, independently of whether
provider credentials are currently configured. Runtime state is layered on
these static capabilities by the financial API facade.
"""

from copy import deepcopy


# This is the implemented-provider catalog, not a claim that every payment
# provider worldwide is implemented. New adapters can be added without
# changing the public state model.
GATEWAY_REGISTRY = {
    "stripe": {
        "id": "stripe",
        "name": "Stripe",
        "provider": "stripe",
        "supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["USD", "EUR", "GBP", "AUD", "CAD", "SGD"],
    },
    "paypal": {
        "id": "paypal",
        "name": "PayPal",
        "provider": "paypal",
        "supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["USD", "EUR", "GBP", "AUD", "CAD"],
    },
    "razorpay": {
        "id": "razorpay",
        "name": "Razorpay",
        "provider": "razorpay",
        "supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["INR", "USD"],
    },
    "sslcommerz": {
        "id": "sslcommerz",
        "name": "SSLCommerz",
        "provider": "sslcommerz",
        "supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["BDT"],
    },
    "bkash": {
        "id": "bkash",
        "name": "bKash",
        "provider": "bkash",
        "supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["BDT"],
    },
    "nagad": {
        "id": "nagad",
        "name": "Nagad",
        "provider": "nagad",
        "supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["BDT"],
    },
    "crypto": {
        "id": "crypto",
        "name": "Crypto / NOWPayments",
        "provider": "crypto",
        "supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["BTC", "ETH", "USDT"],
    },
}

PAYOUT_PROVIDERS = {
    "payoneer": {
        "id": "payoneer",
        "name": "Payoneer",
        "provider": "payoneer",
        "supported": True,
        "capabilities": ["payout"],
    }
}

CURRENCY_REGISTRY = sorted(
    {currency for gateway in GATEWAY_REGISTRY.values() for currency in gateway["currencies"]}
)


def gateway_catalog() -> dict:
    """Return a defensive copy suitable for enriching with runtime state."""
    return deepcopy(GATEWAY_REGISTRY)
