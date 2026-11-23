import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.work_escrow import PayoutIn, ReserveIn, ReleaseIn, reserve_work_budget, router
from app.models.models import TxStatus


class FakeSession:
    def __init__(self, scalar_results):
        self.scalar_results = list(scalar_results)
        self.added = []
        self.commits = 0

    async def scalar(self, _query):
        return self.scalar_results.pop(0)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1


def reserve_body(amount="25.00"):
    return ReserveIn(tenant_id="tenant-1", creator_id="creator-1", work_id="work-1", currency="BDT", amount=amount)


def test_reserve_freezes_full_task_budget_and_writes_idempotent_journal():
    wallet = SimpleNamespace(balance=Decimal("100"), frozen=Decimal("5"), id="wallet-1")
    session = FakeSession([None, wallet, None])
    result = asyncio.run(reserve_work_budget(reserve_body(), session))
    assert result["status"] == "reserved"
    assert result["reserved_amount"] == "25.00"
    assert wallet.frozen == Decimal("30.00")
    assert session.commits == 1
    journal = session.added[0]
    assert journal.status == TxStatus.requires_approval
    assert journal.reference == "work-escrow:work-1"
    assert journal.meta["remaining_amount"] == "25.00"


def test_reserve_retry_is_idempotent_and_does_not_freeze_twice():
    existing = SimpleNamespace(
        currency="BDT", amount=Decimal("25.00"), status=TxStatus.requires_approval,
        meta={"reserved_amount": "25.00", "remaining_amount": "25.00"},
    )
    session = FakeSession([existing])
    result = asyncio.run(reserve_work_budget(reserve_body(), session))
    assert result["duplicate"] is True
    assert result["remaining_amount"] == "25.00"
    assert not session.added
    assert session.commits == 0


def test_reserve_refuses_insufficient_available_balance_without_freezing():
    wallet = SimpleNamespace(balance=Decimal("30"), frozen=Decimal("10"), id="wallet-1")
    session = FakeSession([None, wallet, None])
    with pytest.raises(HTTPException) as error:
        asyncio.run(reserve_work_budget(reserve_body("25"), session))
    assert error.value.status_code == 409
    assert wallet.frozen == Decimal("10")
    assert not session.added
    assert session.commits == 0


def test_escrow_request_contracts_require_positive_amount_and_stable_identifiers():
    assert [route.path for route in router.routes] == ["/reserve", "/payout", "/release-unused"]
    payout = PayoutIn(
        tenant_id="tenant-1", creator_id="creator-1", work_id="work-1",
        recipient_id="worker-1", currency="BDT", amount="7.5",
        idempotency_key="work-escrow-pay:abc12345",
    )
    assert payout.amount == Decimal("7.5")
    with pytest.raises(ValidationError):
        ReserveIn(tenant_id="tenant-1", creator_id="creator-1", work_id="work-1", currency="BDT", amount="0")
    with pytest.raises(ValidationError):
        ReleaseIn(tenant_id="tenant-1", creator_id="creator-1", work_id="work-1")
