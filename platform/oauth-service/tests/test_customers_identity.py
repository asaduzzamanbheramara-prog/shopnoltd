from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api import customers
from app.models.models import UserMirror
from app.schemas.schemas import CustomerIn


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, user):
        self.added = []
        self.execute = AsyncMock(return_value=Result(user))
        self.commit = AsyncMock()
        self.refresh = AsyncMock()

    def add(self, value):
        if getattr(value, "id", None) is None:
            value.id = "customer-row-1"
        if getattr(value, "active", None) is None:
            value.active = True
        self.added.append(value)


@pytest.mark.asyncio
async def test_customer_record_links_to_existing_customers_keycloak_subject(monkeypatch):
    user = UserMirror(
        id="mirror-1",
        keycloak_id="customer-sub-1",
        email="customer@example.com",
        tenant_id="tenant-a",
        active=True,
        name="Customer",
    )
    session = FakeSession(user)
    monkeypatch.setattr(customers, "require_tenant_owner_access", AsyncMock())
    monkeypatch.setattr(customers, "verify_token", AsyncMock(return_value={"sub": "owner-sub"}))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="owner-token")

    result = await customers.create(
        "tenant-a",
        CustomerIn(email=" CUSTOMER@example.com ", name="Customer"),
        credentials,
        session,
    )

    assert result.email == "customer@example.com"
    assert session.added[0].keycloak_id == "customer-sub-1"
    assert session.added[0].keycloak_id != "owner-sub"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_customer_record_rejects_unregistered_or_other_tenant_identity(monkeypatch):
    session = FakeSession(None)
    monkeypatch.setattr(customers, "require_tenant_owner_access", AsyncMock())
    monkeypatch.setattr(customers, "verify_token", AsyncMock(return_value={"sub": "owner-sub"}))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="owner-token")

    with pytest.raises(HTTPException) as exc:
        await customers.create(
            "tenant-a",
            CustomerIn(email="not-registered@example.com"),
            credentials,
            session,
        )

    assert exc.value.status_code == 409
    assert session.added == []
    session.commit.assert_not_awaited()
