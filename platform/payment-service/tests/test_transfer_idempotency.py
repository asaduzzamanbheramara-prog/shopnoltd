from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.transfers import _validate_existing_transfer
from app.schemas.schemas import TransferIn


def existing_transfer(*, to="platform-wallet", currency="USD", amount=Decimal("12.00"), note="Domain registration: example.com (1yr)"):
    return SimpleNamespace(
        meta={"to": to, "note": note},
        currency=currency,
        amount=-amount,
    )


def request(*, to="platform-wallet", currency="USD", amount="12.00", note="Domain registration: example.com (1yr)"):
    return TransferIn(
        to_user_id=to,
        currency=currency,
        amount=Decimal(amount),
        note=note,
        idempotency_key="request-key-0001",
    )


def test_same_key_and_same_payload_can_be_retried():
    _validate_existing_transfer(existing_transfer(), request(), "USD", Decimal("12.00"))


@pytest.mark.parametrize(
    "body,currency,amount",
    [
        (request(to="different-wallet"), "USD", Decimal("12.00")),
        (request(currency="EUR"), "EUR", Decimal("12.00")),
        (request(amount="24.00"), "USD", Decimal("24.00")),
        (request(note="Domain renewal: example.com (1yr)"), "USD", Decimal("12.00")),
    ],
)
def test_same_key_with_changed_payload_is_rejected(body, currency, amount):
    with pytest.raises(HTTPException) as exc:
        _validate_existing_transfer(existing_transfer(), body, currency, amount)
    assert exc.value.status_code == 409
