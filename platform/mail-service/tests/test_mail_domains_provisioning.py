import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_ROOT = REPO_ROOT / "platform" / "mail-service"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
if str(REPO_ROOT / "shared" / "libraries" / "python") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "shared" / "libraries" / "python"))

from app.api import domains


class FakeSession:
    def __init__(self):
        self.domain = None
        self.committed = False
        self.rolled_back = False

    def add(self, domain):
        self.domain = domain

    async def flush(self):
        self.domain.id = "domain-123"

    async def commit(self):
        self.committed = True

    async def refresh(self, _domain):
        return None

    async def rollback(self):
        self.rolled_back = True


def test_domain_is_active_only_after_mailcow_confirms_creation(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(
        domains, "call_mailcow", AsyncMock(return_value=[{"type": "success", "msg": "domain added"}])
    )

    result = asyncio.run(
        domains.add(
            body=SimpleNamespace(name="example.test"),
            user={"tenant_id": "tenant-1"},
            s=session,
        )
    )

    assert session.committed
    assert not session.rolled_back
    assert session.domain.active is True
    assert result == {"id": "domain-123", "name": "example.test", "active": True}


@pytest.mark.parametrize(
    "provider_result",
    [
        [],
        [{"type": "danger", "msg": "internal provider detail"}],
        {"error": "internal provider detail"},
    ],
)
def test_domain_provider_failure_rolls_back_and_returns_sanitized_502(monkeypatch, provider_result):
    session = FakeSession()
    monkeypatch.setattr(domains, "call_mailcow", AsyncMock(return_value=provider_result))

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            domains.add(
                body=SimpleNamespace(name="example.test"),
                user={"tenant_id": "tenant-1"},
                s=session,
            )
        )

    assert caught.value.status_code == 502
    assert caught.value.detail == "mail domain provider provisioning failed"
    assert "internal provider detail" not in caught.value.detail
    assert session.rolled_back
    assert not session.committed


def test_domain_provider_exception_is_not_reported_as_success(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(
        domains,
        "call_mailcow",
        AsyncMock(side_effect=RuntimeError("sensitive provider response")),
    )

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            domains.add(
                body=SimpleNamespace(name="example.test"),
                user={"tenant_id": "tenant-1"},
                s=session,
            )
        )

    assert caught.value.status_code == 502
    assert session.rolled_back
    assert not session.committed
