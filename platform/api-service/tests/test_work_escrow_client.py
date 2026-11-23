import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import work_escrow


def test_reserve_client_uses_full_gross_budget_before_publish(monkeypatch):
    calls = []

    async def fake_request(path, payload):
        calls.append((path, payload))
        return {"status": "reserved", "remaining_amount": payload["amount"]}

    monkeypatch.setattr(work_escrow, "_request", fake_request)
    work = SimpleNamespace(id="work-1", tenant_id="tenant-1", creator_id="creator-1", currency="BDT", reward_amount=Decimal("12.5"), max_workers=4)
    result = asyncio.run(work_escrow.reserve_work_budget(work))
    assert result["status"] == "reserved"
    assert calls[0][0] == "reserve"
    assert calls[0][1]["amount"] == "50.00000000"


def test_escrow_payout_idempotency_key_is_stable_and_scoped_to_work(monkeypatch):
    calls = []

    async def fake_request(path, payload):
        calls.append((path, payload))
        return {"status": "completed"}

    monkeypatch.setattr(work_escrow, "_request", fake_request)
    work = SimpleNamespace(id="work-1", tenant_id="tenant-1", creator_id="creator-1", currency="BDT")
    asyncio.run(work_escrow.payout_work_escrow(work, "worker-1", Decimal("7"), "submission-1", "worker reward"))
    asyncio.run(work_escrow.payout_work_escrow(work, "worker-1", Decimal("7"), "submission-1", "worker reward"))
    assert calls[0][0] == "payout"
    assert calls[0][1]["idempotency_key"] == calls[1][1]["idempotency_key"]
    assert calls[0][1]["amount"] == "7.00000000"


def test_missing_bridge_key_fails_closed(monkeypatch):
    monkeypatch.delenv("PAYMENT_INTERNAL_API_KEY", raising=False)
    with pytest.raises(HTTPException) as error:
        work_escrow._headers()
    assert "not configured" in error.value.detail
