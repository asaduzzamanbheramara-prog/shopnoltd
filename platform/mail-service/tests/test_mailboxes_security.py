import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import mailboxes


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, domain):
        self.domain = domain
        self.added = []
        self.committed = False
        self.rolled_back = False
        self.refreshed = False

    async def execute(self, _statement):
        return FakeResult(self.domain)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, _value):
        self.refreshed = True


def run(coro):
    return asyncio.run(coro)


def setup(monkeypatch, provider):
    domain = SimpleNamespace(id="domain-1", name="example.test")
    session = FakeSession(domain)
    monkeypatch.setattr(mailboxes, "call_mailcow", provider)
    return session


def test_mailbox_uses_random_provider_password_and_does_not_return_it(monkeypatch):
    captured = {}

    async def provider(action, payload):
        captured.update(action=action, payload=payload)
        return {"success": True}

    session = setup(monkeypatch, provider)
    result = run(
        mailboxes.add(
            "domain-1",
            mailboxes.MailboxIn(local_part="alice", quota_mb=512),
            user={"tenant_id": "tenant-1"},
            s=session,
        )
    )

    assert captured["action"] == "add/mailbox"
    password = captured["payload"]["password"]
    assert password != "change-me-immediately"
    assert len(password) >= 32
    assert captured["payload"]["password2"] == password
    assert "password" not in result
    assert result["active"] is True
    assert session.committed is True
    assert session.rolled_back is False


def test_provider_failure_rolls_back_and_never_reports_success(monkeypatch):
    async def provider(_action, _payload):
        raise RuntimeError("provider unavailable")

    session = setup(monkeypatch, provider)
    with pytest.raises(HTTPException) as raised:
        run(
            mailboxes.add(
                "domain-1",
                mailboxes.MailboxIn(local_part="alice", quota_mb=512),
                user={"tenant_id": "tenant-1"},
                s=session,
            )
        )

    assert raised.value.status_code == 502
    assert "provider unavailable" not in raised.value.detail
    assert session.rolled_back is True
    assert session.committed is False


def test_nonpositive_quota_is_rejected_before_provider_call(monkeypatch):
    calls = []

    async def provider(action, payload):
        calls.append((action, payload))
        return {"success": True}

    session = setup(monkeypatch, provider)
    with pytest.raises(HTTPException) as raised:
        run(
            mailboxes.add(
                "domain-1",
                mailboxes.MailboxIn(local_part="alice", quota_mb=0),
                user={"tenant_id": "tenant-1"},
                s=session,
            )
        )

    assert raised.value.status_code == 422
    assert calls == []
    assert session.committed is False
