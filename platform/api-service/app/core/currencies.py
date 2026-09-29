"""Shared currency registry for all Shopnoltd services exposed by the unified API.

Task rates, marketplace work, checkout and payment-facing APIs must consume the
same registry so the platform remains globally multi-currency instead of
assuming a single country or currency.
"""

SUPPORTED_CURRENCIES = frozenset({
    "USD", "BDT", "EUR", "GBP", "INR", "AUD", "CAD", "SGD", "AED", "SAR",
    "JPY", "CNY", "HKD", "MYR", "THB", "IDR", "PKR", "NPR", "LKR", "QAR",
    "KWD", "OMR", "NZD", "CHF", "SEK", "NOK", "DKK", "ZAR", "TRY", "BRL",
})
