"""Live payment method / gateway listing for the checkout UI."""

from app.providers.registry import _REG, supported_deposit_currencies
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_methods():
    out = []
    for method, provider in _REG.items():
        out.append(
            {
                "id": method.value,
                "display_name": method.value.replace("_", " ").title(),
                "enabled": getattr(provider, "enabled", True),
                "currencies": sorted(supported_deposit_currencies(method)),
            }
        )
    return {"methods": out}
