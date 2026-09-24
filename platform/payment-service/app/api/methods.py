"""Live payment method / gateway listing for the checkout UI."""

from app.providers.registry import _REG, supported_deposit_currencies
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_methods():
    out = []
    for method, provider in _REG.items():
        currencies = sorted(supported_deposit_currencies(method))
        # A method is customer-checkout-enabled only when its provider has
        # explicitly opted in and it has at least one supported deposit
        # currency. This excludes unconfigured gateways and payout-only
        # integrations such as Payoneer from the checkout capability list.
        enabled = bool(getattr(provider, "enabled", False) and currencies)
        out.append(
            {
                "id": method.value,
                "display_name": method.value.replace("_", " ").title(),
                "enabled": enabled,
                "currencies": currencies,
            }
        )
    return {"methods": out}
