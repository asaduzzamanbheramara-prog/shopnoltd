"""Canonical financial gateway and currency metadata."""

from copy import deepcopy


GATEWAY_REGISTRY = {
    "stripe": {
        "id": "stripe", "name": "Stripe", "provider": "stripe", "supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["USD", "EUR", "GBP", "AUD", "CAD", "SGD"],
    },
    "paypal": {
        "id": "paypal", "name": "PayPal", "provider": "paypal", "supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["USD", "EUR", "GBP", "AUD", "CAD"],
    },
    "razorpay": {
        "id": "razorpay", "name": "Razorpay", "provider": "razorpay", "supported": True,
        "capabilities": ["checkout", "webhook"], "currencies": ["INR", "USD"],
    },
    "sslcommerz": {
        "id": "sslcommerz", "name": "SSLCommerz", "provider": "sslcommerz", "supported": True,
        "capabilities": ["checkout", "webhook"], "currencies": ["BDT"],
    },
    "bkash": {
        "id": "bkash", "name": "bKash", "provider": "bkash", "supported": True,
        "capabilities": ["checkout", "webhook"], "currencies": ["BDT"],
    },
    "nagad": {
        "id": "nagad", "name": "Nagad", "provider": "nagad", "supported": True,
        "capabilities": ["checkout", "webhook"], "currencies": ["BDT"],
    },
    "moneybag": {
        "id": "moneybag", "name": "Moneybag", "provider": "moneybag", "supported": True,
        "capabilities": ["checkout", "webhook"], "currencies": ["BDT"],
        "payment_methods": [
            "visa", "mastercard", "amex", "unionpay", "diners_club", "dbbl_nexus",
            "bkash", "nagad", "rocket", "upay", "tap",
        ],
    },
    "crypto": {
        "id": "crypto", "name": "Crypto / NOWPayments", "provider": "crypto", "supported": True,
        "capabilities": ["checkout", "webhook"], "currencies": ["BTC", "ETH", "USDT"],
    },
}

PAYOUT_PROVIDERS = {
    "payoneer": {
        "id": "payoneer", "name": "Payoneer", "provider": "payoneer",
        "supported": True, "capabilities": ["payout"],
    }
}

CURRENCY_REGISTRY = sorted(
    {currency for gateway in GATEWAY_REGISTRY.values() for currency in gateway["currencies"]}
)


def gateway_catalog() -> dict:
    return deepcopy(GATEWAY_REGISTRY)
