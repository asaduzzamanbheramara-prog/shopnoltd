"""
Live currency exchange rates, replacing the old hardcoded EXCHANGE_RATES dict.

Uses exchangerate.host (or any Open Exchange Rates-compatible API set via
EXCHANGE_RATE_API_KEY). Falls back to the last successfully fetched rates
(or a static snapshot on first-ever failure) so the API never crashes just
because an external FX provider had a blip -- but every response says
whether the numbers are `"live": true` or `"live": false, "stale_since": ...`
so nobody mistakes a fallback for a fresh rate.
"""

import time

import requests

from app import config

# Static snapshot used only if the live API has never succeeded yet.
_FALLBACK_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "BDT": 109.5,
    "INR": 83.2,
    "JPY": 149.5,
    "CNY": 7.24,
    "AUD": 1.52,
    "CAD": 1.37,
    "SGD": 1.34,
    "MYR": 4.72,
    "PKR": 278.5,
    "LKR": 308.0,
    "NPR": 133.0,
    "AED": 3.67,
    "SAR": 3.75,
}

CURRENCY_INFO = {
    "USD": {"name": "US Dollar", "symbol": "$", "flag": "\U0001f1fa\U0001f1f8"},
    "EUR": {"name": "Euro", "symbol": "\u20ac", "flag": "\U0001f1ea\U0001f1fa"},
    "GBP": {"name": "British Pound", "symbol": "\u00a3", "flag": "\U0001f1ec\U0001f1e7"},
    "BDT": {"name": "Bangladeshi Taka", "symbol": "\u09f3", "flag": "\U0001f1e7\U0001f1e9"},
    "INR": {"name": "Indian Rupee", "symbol": "\u20b9", "flag": "\U0001f1ee\U0001f1f3"},
    "JPY": {"name": "Japanese Yen", "symbol": "\u00a5", "flag": "\U0001f1ef\U0001f1f5"},
    "CNY": {"name": "Chinese Yuan", "symbol": "\u00a5", "flag": "\U0001f1e8\U0001f1f3"},
    "AUD": {"name": "Australian Dollar", "symbol": "A$", "flag": "\U0001f1e6\U0001f1fa"},
    "CAD": {"name": "Canadian Dollar", "symbol": "C$", "flag": "\U0001f1e8\U0001f1e6"},
    "SGD": {"name": "Singapore Dollar", "symbol": "S$", "flag": "\U0001f1f8\U0001f1ec"},
}

_cache = {"rates": dict(_FALLBACK_RATES), "fetched_at": None, "live": False}


def _fetch_live_rates() -> dict:
    resp = requests.get(
        "https://openexchangerates.org/api/latest.json",
        params={"app_id": config.EXCHANGE_RATE_API_KEY, "base": "USD"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["rates"]


def get_rates() -> dict:
    """Returns {"rates": {...}, "live": bool, "fetched_at": iso_or_None}."""
    if not config.EXCHANGE_RATE_LIVE_ENABLED:
        return {
            "rates": _cache["rates"],
            "live": False,
            "fetched_at": None,
            "note": "EXCHANGE_RATE_API_KEY not set - using a static snapshot, not live rates.",
        }

    stale = (
        _cache["fetched_at"] is None
        or (time.time() - _cache["fetched_at"]) > config.EXCHANGE_RATE_CACHE_SECONDS
    )
    if stale:
        try:
            live_rates = _fetch_live_rates()
            _cache["rates"] = live_rates
            _cache["fetched_at"] = time.time()
            _cache["live"] = True
        except Exception:
            # Keep serving the last good cache (or the static fallback) rather than failing the request.
            pass

    return {
        "rates": _cache["rates"],
        "live": _cache["live"],
        "fetched_at": _cache["fetched_at"],
    }


def convert_currency(amount: float, from_curr: str, to_curr: str):
    rates = get_rates()["rates"]
    if from_curr not in rates or to_curr not in rates:
        raise ValueError(f"Unsupported currency: {from_curr} or {to_curr}")
    if from_curr == to_curr:
        return amount, 1.0
    usd_amount = amount / rates[from_curr]
    converted = usd_amount * rates[to_curr]
    rate = rates[to_curr] / rates[from_curr]
    return round(converted, 2), round(rate, 6)
