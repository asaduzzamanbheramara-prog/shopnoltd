from decimal import Decimal

from app.services.billing_service import BillingService


def key(user_id="user-1", operation="renew", request_key="request-0001", domain="example.com", years=1, currency="USD", amount=Decimal("12.00")):
    return BillingService._idempotency_key(user_id, operation, request_key, domain, years, currency, amount)


def test_same_request_reuses_same_charge_key():
    assert key() == key()


def test_distinct_renewal_requests_do_not_reuse_old_charge_key():
    assert key(request_key="renew-0001") != key(request_key="renew-0002")


def test_registration_and_renewal_are_separate_operations():
    assert key(operation="register") != key(operation="renew")


def test_idempotency_is_scoped_to_the_authenticated_user():
    assert key(user_id="user-1") != key(user_id="user-2")


def test_same_request_key_is_independent_of_payload_and_payment_service_validates_payload():
    assert key(amount=Decimal("12.00")) == key(amount=Decimal("24.00"))
    assert key(years=1) == key(years=2)
