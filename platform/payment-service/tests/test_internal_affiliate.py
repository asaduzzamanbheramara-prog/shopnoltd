import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.internal_affiliate import AffiliateWalletCredit, router
from app.core.config import settings
from app.core.security import require_affiliate_payment_key


def test_affiliate_wallet_credit_is_credit_only_and_idempotent_contract():
    body = AffiliateWalletCredit(
        user_id="user-123",
        currency="usd",
        amount="0.7000",
        idempotency_key="affiliate:adgem:req:user-reward",
        reference="Affiliate reward adgem:req",
    )
    assert body.currency == "usd"
    assert body.amount > 0
    assert body.idempotency_key.startswith("affiliate:")
    assert [route.path for route in router.routes] == ["/wallet-credit"]
    with pytest.raises(ValidationError):
        AffiliateWalletCredit(
            user_id="user-123", currency="USD", amount="-1",
            idempotency_key="affiliate:invalid", reference="invalid",
        )


def test_affiliate_payment_bridge_uses_separate_secret(monkeypatch):
    monkeypatch.setattr(settings, "affiliate_internal_api_key", "test-only-affiliate-bridge-key")
    assert require_affiliate_payment_key("test-only-affiliate-bridge-key") is True
    with pytest.raises(HTTPException) as error:
        require_affiliate_payment_key("wrong-key")
    assert error.value.status_code == 403
