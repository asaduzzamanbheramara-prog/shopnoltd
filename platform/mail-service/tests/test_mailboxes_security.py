import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

# Allow pytest to run from the repository root or this service directory.
SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

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
        return [{"type": "success", "msg": "mailbox added"}]

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


def test_provider_exception_rolls_back_and_never_reports_success(monkeypatch):
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


@pytest.mark.parametrize(
    "provider_response",
    [
        [{"type": "error", "msg": "mailbox already exists"}],
        {"success": True},
        [],
    ],
)
def test_provider_non_success_response_rolls_back(monkeypatch, provider_response):
    async def provider(_action, _payload):
        return provider_response

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
    assert session.rolled_back is True
    assert session.committed is False


def test_nonpositive_quota_is_rejected_before_provider_call(monkeypatch):
    calls = []

    async def provider(action, payload):
        calls.append((action, payload))
        return [{"type": "success", "msg": "mailbox added"}]

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



def test_mailcow_placeholder_key_fails_closed_before_network_call(monkeypatch):
    from app.core import mailcow

    monkeypatch.setattr(mailcow.settings, "mailcow_api_key", "CHANGE_ME_MAILCOW_KEY")

    class NetworkMustNotBeUsed:
        def __init__(self, *args, **kwargs):
            raise AssertionError("network client must not be created with a placeholder key")

    monkeypatch.setattr(mailcow.httpx, "AsyncClient", NetworkMustNotBeUsed)
    with pytest.raises(RuntimeError, match="API key is not configured"):
        run(mailcow.call_mailcow("add/mailbox", {"local_part": "alice"}))


def test_mailcow_blank_key_fails_closed(monkeypatch):
    from app.core import mailcow

    monkeypatch.setattr(mailcow.settings, "mailcow_api_key", "   ")
    with pytest.raises(RuntimeError, match="API key is not configured"):
        run(mailcow.call_mailcow("add/mailbox", {"local_part": "alice"}))

def test_mailbox_listing_requires_admin_authentication():
    import inspect
    from fastapi.params import Depends

    parameter = inspect.signature(mailboxes.list_mb).parameters["user"]
    assert isinstance(parameter.default, Depends)
    assert parameter.default.dependency is mailboxes.admin


def test_admin_can_assign_existing_mailbox_owner(monkeypatch):
    from types import SimpleNamespace
    from app.schemas.schemas import MailboxOwnerIn

    mailbox = SimpleNamespace(
        id="mailbox-1",
        full_address="alice@example.test",
        owner_user_id=None,
    )
    session = FakeSession(mailbox)
    result = run(
        mailboxes.assign_owner(
            "mailbox-1",
            MailboxOwnerIn(owner_user_id="keycloak-subject-1"),
            user={"tenant_id": "tenant-1"},
            s=session,
        )
    )
    assert mailbox.owner_user_id == "keycloak-subject-1"
    assert result["owner_user_id"] == "keycloak-subject-1"
    assert session.committed is True


def test_mailbox_owner_assignment_requires_admin_dependency():
    import inspect
    from fastapi.params import Depends

    parameter = inspect.signature(mailboxes.assign_owner).parameters["user"]
    assert isinstance(parameter.default, Depends)
    assert parameter.default.dependency is mailboxes.admin
