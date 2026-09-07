"""Canonical financial gateway, payment-method and currency metadata.

The catalogue is deliberately broader than the set of adapters that are live
in this deployment.  ``implemented`` answers whether Shopnoltd has an adapter;
``provider_supported`` answers whether the provider/method belongs to the
supported platform catalogue.  Runtime configuration is layered on top by the
financial API facade.
"""

from copy import deepcopy


CHECKOUT_OPERATIONS = [
    "checkout",
    "authorize",
    "capture",
    "verify",
    "refund",
    "void",
    "recurring",
    "webhook",
    "reconciliation",
    "dispute",
    "settlement",
]


PAYMENT_METHOD_REGISTRY = {
    "card": {"id": "card", "name": "Card", "category": "card_network_instrument"},
    "visa": {"id": "visa", "name": "Visa", "category": "card_network"},
    "mastercard": {"id": "mastercard", "name": "Mastercard", "category": "card_network"},
    "amex": {"id": "amex", "name": "American Express", "category": "card_network"},
    "discover": {"id": "discover", "name": "Discover", "category": "card_network"},
    "jcb": {"id": "jcb", "name": "JCB", "category": "card_network"},
    "unionpay": {"id": "unionpay", "name": "UnionPay", "category": "card_network"},
    "diners_club": {"id": "diners_club", "name": "Diners Club", "category": "card_network"},
    "bank_transfer": {"id": "bank_transfer", "name": "Bank Transfer", "category": "bank_rail"},
    "ach": {"id": "ach", "name": "ACH", "category": "bank_rail"},
    "sepa": {"id": "sepa", "name": "SEPA", "category": "bank_rail"},
    "swift": {"id": "swift", "name": "SWIFT", "category": "bank_rail"},
    "faster_payments": {"id": "faster_payments", "name": "Faster Payments", "category": "bank_rail"},
    "mobile_wallet": {"id": "mobile_wallet", "name": "Mobile Wallet", "category": "wallet"},
    "bkash": {"id": "bkash", "name": "bKash", "category": "mobile_wallet"},
    "nagad": {"id": "nagad", "name": "Nagad", "category": "mobile_wallet"},
    "rocket": {"id": "rocket", "name": "Rocket", "category": "mobile_wallet"},
    "upay": {"id": "upay", "name": "upay", "category": "mobile_wallet"},
    "google_pay": {"id": "google_pay", "name": "Google Pay", "category": "digital_wallet"},
    "apple_pay": {"id": "apple_pay", "name": "Apple Pay", "category": "digital_wallet"},
    "samsung_pay": {"id": "samsung_pay", "name": "Samsung Pay", "category": "digital_wallet"},
    "paypal_wallet": {"id": "paypal_wallet", "name": "PayPal Wallet", "category": "digital_wallet"},
    "amazon_pay": {"id": "amazon_pay", "name": "Amazon Pay", "category": "digital_wallet"},
    "alipay": {"id": "alipay", "name": "Alipay", "category": "digital_wallet"},
    "wechat_pay": {"id": "wechat_pay", "name": "WeChat Pay", "category": "digital_wallet"},
    "crypto": {"id": "crypto", "name": "Cryptocurrency", "category": "crypto"},
    "dbbl_nexus": {"id": "dbbl_nexus", "name": "DBBL Nexus", "category": "local_method"},
    "rocket": {"id": "rocket", "name": "Rocket", "category": "local_method"},
    "tap": {"id": "tap", "name": "TAP", "category": "local_method"},
}


# ``implemented`` means an actual Shopnoltd adapter exists today.  Catalogue-
# only providers stay visible with ``implemented=False`` so enabling them later
# does not require changing the public financial contract.
GATEWAY_REGISTRY = {
    "stripe": {
        "id": "stripe", "name": "Stripe", "provider": "stripe",
        "implemented": True, "provider_supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["USD", "EUR", "GBP", "AUD", "CAD", "SGD"],
        "payment_methods": ["card", "visa", "mastercard", "amex", "discover", "google_pay", "apple_pay"],
    },
    "paypal": {
        "id": "paypal", "name": "PayPal", "provider": "paypal",
        "implemented": True, "provider_supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["USD", "EUR", "GBP", "AUD", "CAD"],
        "payment_methods": ["paypal_wallet", "card", "visa", "mastercard", "amex"],
    },
    "razorpay": {
        "id": "razorpay", "name": "Razorpay", "provider": "razorpay",
        "implemented": True, "provider_supported": True,
        "capabilities": ["checkout", "webhook"],
        "currencies": ["INR", "USD"],
        "payment_methods": ["card", "visa", "mastercard", "amex", "upi", "bank_transfer", "mobile_wallet"],
    },
    "sslcommerz": {
        "id": "sslcommerz", "name": "SSLCommerz", "provider": "sslcommerz",
        "implemented": True, "provider_supported": True,
        "capabilities": ["checkout", "webhook"], "currencies": ["BDT"],
        "payment_methods": ["card", "visa", "mastercard", "amex", "dbbl_nexus", "bkash", "nagad", "rocket", "bank_transfer"],
    },
    "bkash": {
        "id": "bkash", "name": "bKash", "provider": "bkash",
        "implemented": True, "provider_supported": True,
        "capabilities": ["checkout", "webhook"], "currencies": ["BDT"],
        "payment_methods": ["bkash", "mobile_wallet"],
    },
    "nagad": {
        "id": "nagad", "name": "Nagad", "provider": "nagad",
        "implemented": True, "provider_supported": True,
        "capabilities": ["checkout", "webhook"], "currencies": ["BDT"],
        "payment_methods": ["nagad", "mobile_wallet"],
    },
    "moneybag": {
        "id": "moneybag", "name": "Moneybag", "provider": "moneybag",
        "implemented": True, "provider_supported": True,
        "capabilities": ["checkout", "webhook"], "currencies": ["BDT"],
        "payment_methods": ["visa", "mastercard", "amex", "unionpay", "diners_club", "dbbl_nexus", "bkash", "nagad", "rocket", "upay", "tap"],
    },
    "crypto": {
        "id": "crypto", "name": "Crypto / NOWPayments", "provider": "crypto",
        "implemented": True, "provider_supported": True,
        "capabilities": ["checkout", "webhook"], "currencies": ["BTC", "ETH", "USDT"],
        "payment_methods": ["crypto"],
    },
}


# Major processors are retained in the catalogue before credentials or a
# provider-specific adapter are installed.  Their live availability remains
# false until an adapter and runtime configuration exist.
CATALOG_ONLY_GATEWAYS = {
    "adyen": ("Adyen", ["card", "google_pay", "apple_pay", "alipay", "wechat_pay", "bank_transfer"]),
    "checkout_com": ("Checkout.com", ["card", "google_pay", "apple_pay", "bank_transfer"]),
    "braintree": ("Braintree", ["card", "paypal_wallet", "google_pay", "apple_pay"]),
    "square": ("Square", ["card", "google_pay", "apple_pay"]),
    "mollie": ("Mollie", ["card", "google_pay", "apple_pay", "paypal_wallet", "bank_transfer"]),
    "worldpay": ("Worldpay", ["card", "google_pay", "apple_pay", "bank_transfer"]),
    "authorize_net": ("Authorize.Net", ["card", "apple_pay", "google_pay"]),
    "2checkout": ("2Checkout / Verifone", ["card", "paypal_wallet"]),
    "airwallex": ("Airwallex", ["card", "bank_transfer"]),
    "payu": ("PayU", ["card", "bank_transfer", "mobile_wallet"]),
    "payeer": ("Payeer", ["digital_wallet", "crypto"]),
    "binance_pay": ("Binance Pay", ["crypto"]),
    "nowpayments": ("NOWPayments", ["crypto"]),
    "wise": ("Wise", ["bank_transfer"]),
    "skrill": ("Skrill", ["digital_wallet"]),
    "neteller": ("Neteller", ["digital_wallet"]),
    "amazon_pay": ("Amazon Pay", ["amazon_pay"]),
}

for gateway_id, (name, methods) in CATALOG_ONLY_GATEWAYS.items():
    GATEWAY_REGISTRY[gateway_id] = {
        "id": gateway_id,
        "name": name,
        "provider": gateway_id,
        "implemented": False,
        "provider_supported": True,
        "capabilities": CHECKOUT_OPERATIONS.copy(),
        "currencies": [],
        "currency_mode": "provider_defined",
        "payment_methods": methods,
    }


PAYOUT_PROVIDERS = {
    "payoneer": {
        "id": "payoneer", "name": "Payoneer", "provider": "payoneer",
        "implemented": True, "provider_supported": True,
        "capabilities": ["payout", "reconciliation", "settlement"],
    },
}


CURRENCY_REGISTRY = sorted(
    {currency for gateway in GATEWAY_REGISTRY.values() for currency in gateway["currencies"]}
)


def gateway_catalog() -> dict:
    """Return a defensive copy suitable for enriching with runtime state."""
    return deepcopy(GATEWAY_REGISTRY)


def payment_method_catalog() -> dict:
    """Return the complete platform payment-method catalogue."""
    return deepcopy(PAYMENT_METHOD_REGISTRY)
