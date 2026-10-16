"""Server-side domain quote validation.

Premium registration prices returned by availability checks are not a verified
multi-year quote. Fail closed rather than applying a single premium price to a
longer registration term.
"""
from decimal import Decimal, InvalidOperation


def registration_quote(availability: dict, pricing: dict, years: int) -> tuple[Decimal, str]:
    if years < 1 or years > 10:
        raise ValueError("Registration duration must be between 1 and 10 years")

    currency = str(pricing.get("currency") or "USD").upper()
    if availability.get("premium"):
        if years != 1:
            raise ValueError(
                "Premium domain pricing is only verified for a one-year registration; "
                "multi-year premium quotes are unavailable"
            )
        raw_price = availability.get("premium_price")
        if raw_price is None:
            raise ValueError("Registrar did not provide a verified premium registration price")
    else:
        raw_price = pricing.get("price")

    try:
        amount = Decimal(str(raw_price))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Registrar returned an invalid domain price") from exc

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Registrar returned a non-positive or invalid domain price")
    return amount, currency
