import os
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/postgres")

from app.api.service_orders import (
    ServiceOrderCreate,
    ServiceOrderQuote,
    _is_platform_admin,
    _same_request,
    _serialize,
    _tenant,
    _user_id,
    is_service_admin,
    router,
)


def valid_request(**overrides):
    values = {
        "service_code": "os_installation",
        "contact_name": "Shopnoltd Customer",
        "contact_email": "customer@example.com",
        "device_platform": "Windows laptop",
        "details": "Please assess and install a supported operating system.",
        "request_key": "req-12345678",
    }
    values.update(overrides)
    return values


def test_customer_request_accepts_only_catalogue_service_codes():
    request = ServiceOrderCreate(**valid_request())
    assert request.service_code == "os_installation"
    with pytest.raises(ValidationError):
        ServiceOrderCreate(**valid_request(service_code="unlisted_service"))


def test_customer_cannot_supply_or_override_quote_price():
    with pytest.raises(ValidationError):
        ServiceOrderCreate(**valid_request(quoted_amount="0.01", quote_currency="BDT"))


def test_request_rejects_invalid_email_and_blank_contact_name():
    with pytest.raises(ValidationError):
        ServiceOrderCreate(**valid_request(contact_email="not-an-email"))
    with pytest.raises(ValidationError):
        ServiceOrderCreate(**valid_request(contact_name="   "))


def test_request_key_is_required_to_be_safe_and_bounded():
    with pytest.raises(ValidationError):
        ServiceOrderCreate(**valid_request(request_key="bad key"))
    with pytest.raises(ValidationError):
        ServiceOrderCreate(**valid_request(request_key="x"))


def test_quote_amount_and_expiry_are_server_validated():
    quote = ServiceOrderQuote(amount=Decimal("1250.50"), currency="BDT", expires_in_days=7)
    assert quote.amount == Decimal("1250.50")
    with pytest.raises(ValidationError):
        ServiceOrderQuote(amount=Decimal("0"))
    with pytest.raises(ValidationError):
        ServiceOrderQuote(amount=Decimal("1"), expires_in_days=31)
    with pytest.raises(ValidationError):
        ServiceOrderQuote(amount=Decimal("1"), currency="EUR")


def test_admin_roles_and_platform_admin_scope_are_distinct():
    tenant_admin = {"sub": "tenant-admin", "tenant_id": "tenant-a", "roles": ["tenant_admin"]}
    platform_admin = {"sub": "platform-admin", "tenant_id": "default", "realm_access": {"roles": ["platform_admin"]}}
    customer = {"sub": "customer", "tenant_id": "tenant-a", "roles": []}
    assert is_service_admin(tenant_admin)
    assert not _is_platform_admin(tenant_admin)
    assert is_service_admin(platform_admin)
    assert _is_platform_admin(platform_admin)
    assert not is_service_admin(customer)
    assert not is_service_admin({"sub": "ordinary", "roles": ["admin"]})
    assert not is_service_admin({"sub": "ordinary", "is_admin": True})


def test_identity_is_derived_from_verified_claims():
    user = {"sub": "keycloak-user-123", "tenant_id": "tenant-a"}
    assert _user_id(user) == "keycloak-user-123"
    assert _tenant(user) == "tenant-a"
    with pytest.raises(Exception):
        _user_id({"tenant_id": "tenant-a"})


def test_idempotency_compares_request_content():
    request = ServiceOrderCreate(**valid_request())
    order = SimpleNamespace(
        service_code=request.service_code,
        contact_name=request.contact_name,
        contact_email=request.contact_email,
        device_platform=request.device_platform,
        details=request.details,
    )
    assert _same_request(order, request)
    assert not _same_request(order, ServiceOrderCreate(**valid_request(details="A different request description.")))


def test_customer_response_does_not_expose_tenant_or_internal_customer_identity():
    order = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        tenant_id="tenant-a",
        service_code="os_installation",
        contact_name="Customer",
        contact_email="customer@example.com",
        device_platform="Laptop",
        details="Please install a supported OS.",
        status="requested",
        quoted_amount=None,
        quote_currency=None,
        customer_message=None,
        quote_version=0,
        quoted_at=None,
        quote_expires_at=None,
        accepted_at=None,
        declined_at=None,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )
    result = _serialize(order)
    assert result["id"] == order.id
    assert result["payment_status"] == "not_collected"
    assert "tenant_id" not in result
    assert "customer_id" not in result

def test_router_registers_customer_and_admin_service_order_endpoints():
    paths = {route.path for route in router.routes}
    assert '/service-orders' in paths
    assert '/service-orders/{order_id}' in paths
    assert '/service-orders/{order_id}/accept' in paths
    assert '/service-orders/admin/list' in paths
    assert '/service-orders/admin/{order_id}/quote' in paths
