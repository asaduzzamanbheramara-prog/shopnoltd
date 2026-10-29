import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.api.messages import ensure_mailbox_access


def mailbox(*, owner_user_id=None, tenant_id="tenant-1"):
    return SimpleNamespace(owner_user_id=owner_user_id, tenant_id=tenant_id)


def test_owner_can_access_assigned_mailbox():
    ensure_mailbox_access(mailbox(owner_user_id="user-1"), {"sub": "user-1", "tenant_id": "tenant-1"})


def test_other_user_cannot_access_mailbox():
    with pytest.raises(HTTPException) as caught:
        ensure_mailbox_access(mailbox(owner_user_id="user-1"), {"sub": "user-2", "tenant_id": "tenant-1"})
    assert caught.value.status_code == 404
    assert caught.value.detail == "mailbox not found"


def test_unassigned_legacy_mailbox_is_not_visible_to_regular_users():
    with pytest.raises(HTTPException) as caught:
        ensure_mailbox_access(mailbox(), {"sub": "user-1", "tenant_id": "tenant-1"})
    assert caught.value.status_code == 404


def test_tenant_mismatch_is_not_visible_even_if_owner_claim_matches():
    with pytest.raises(HTTPException) as caught:
        ensure_mailbox_access(mailbox(owner_user_id="user-1", tenant_id="tenant-2"), {"sub": "user-1", "tenant_id": "tenant-1"})
    assert caught.value.status_code == 404


@pytest.mark.parametrize("role", ["admin", "platform_admin"])
def test_platform_admin_can_manage_unassigned_legacy_mailboxes(role):
    ensure_mailbox_access(mailbox(), {"sub": "admin-1", "realm_access": {"roles": [role]}})

def test_unrelated_client_admin_role_does_not_grant_mailbox_access():
    with pytest.raises(HTTPException) as caught:
        ensure_mailbox_access(
            mailbox(),
            {"sub": "user-1", "resource_access": {"unrelated-client": {"roles": ["admin"]}}},
        )
    assert caught.value.status_code == 404


def test_mail_service_admin_role_can_access_mailbox():
    ensure_mailbox_access(
        mailbox(),
        {"sub": "admin-1", "resource_access": {"mail-service": {"roles": ["platform_admin"]}}},
    )

def test_smtp_sender_fails_closed_without_configuration(monkeypatch):
    from app.api import messages

    monkeypatch.setattr(messages.settings, "smtp_host", "")
    monkeypatch.setattr(messages.settings, "smtp_envelope_from", "")
    with pytest.raises(RuntimeError, match="SMTP delivery is not configured"):
        messages._send_smtp_message("alice@example.test", "bob@example.test", "Hi", "Body")


def test_smtp_sender_uses_starttls_and_configured_envelope_sender(monkeypatch):
    from app.api import messages

    calls = {}
    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls["connection"] = (host, port, timeout)
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def ehlo(self):
            calls["ehlo"] = calls.get("ehlo", 0) + 1
        def starttls(self, context):
            calls["starttls"] = context
        def login(self, username, password):
            calls["login"] = (username, password)
        def send_message(self, message, from_addr, to_addrs):
            calls["message"] = (message, from_addr, to_addrs)

    monkeypatch.setattr(messages.settings, "smtp_host", "smtp.example.test")
    monkeypatch.setattr(messages.settings, "smtp_port", 587)
    monkeypatch.setattr(messages.settings, "smtp_username", "smtp-user")
    monkeypatch.setattr(messages.settings, "smtp_password", "smtp-pass")
    monkeypatch.setattr(messages.settings, "smtp_envelope_from", "relay@example.test")
    monkeypatch.setattr(messages.settings, "smtp_timeout_seconds", 9)
    monkeypatch.setattr(messages.smtplib, "SMTP", FakeSMTP)

    messages._send_smtp_message("alice@example.test", "bob@example.test", "Hello", "Message body")

    assert calls["connection"] == ("smtp.example.test", 587, 9)
    assert calls["ehlo"] == 2
    assert calls["login"] == ("smtp-user", "smtp-pass")
    message, envelope_from, recipients = calls["message"]
    assert message["From"] == "alice@example.test"
    assert message["To"] == "bob@example.test"
    assert message["Subject"] == "Hello"
    assert envelope_from == "relay@example.test"
    assert recipients == ["bob@example.test"]


def test_smtp_sender_rejects_header_injection_and_multiple_recipients(monkeypatch):
    from app.api import messages

    monkeypatch.setattr(messages.settings, "smtp_host", "smtp.example.test")
    monkeypatch.setattr(messages.settings, "smtp_envelope_from", "relay@example.test")
    monkeypatch.setattr(messages.settings, "smtp_username", "")
    monkeypatch.setattr(messages.settings, "smtp_password", "")
    with pytest.raises(ValueError, match="recipient address is invalid"):
        messages._send_smtp_message("alice@example.test", "bob@example.test\\r\\nBcc: evil@example.test", "Hi", "Body")
    with pytest.raises(ValueError, match="recipient address is invalid"):
        messages._send_smtp_message("alice@example.test", "bob@example.test,evil@example.test", "Hi", "Body")


def test_send_endpoint_uses_smtp_after_owner_authorization(monkeypatch):
    import asyncio
    from app.api import messages

    mailbox = SimpleNamespace(
        id="mailbox-1",
        tenant_id="tenant-1",
        owner_user_id="user-1",
        full_address="alice@example.test",
        active=True,
    )
    calls = []
    async def accessible(mailbox_id, user, _session):
        assert mailbox_id == "mailbox-1"
        messages.ensure_mailbox_access(mailbox, user)
        return mailbox
    def smtp(from_addr, to_addr, subject, body):
        calls.append((from_addr, to_addr, subject, body))
    monkeypatch.setattr(messages, "accessible_mailbox", accessible)
    monkeypatch.setattr(messages, "_send_smtp_message", smtp)

    result = asyncio.run(
        messages.send(
            from_mailbox_id="mailbox-1",
            to="bob@example.test",
            subject="Test",
            body="Hello",
            user={"sub": "user-1", "tenant_id": "tenant-1"},
            s=object(),
        )
    )
    assert result == {"ok": True, "from": "alice@example.test", "to": "bob@example.test"}
    assert calls == [("alice@example.test", "bob@example.test", "Test", "Hello")]

def test_send_endpoint_rejects_subject_header_injection(monkeypatch):
    import asyncio
    from fastapi import HTTPException
    from app.api import messages

    mailbox = SimpleNamespace(
        id="mailbox-1", tenant_id="tenant-1", owner_user_id="user-1",
        full_address="alice@example.test", active=True,
    )
    async def accessible(_mailbox_id, user, _session):
        messages.ensure_mailbox_access(mailbox, user)
        return mailbox
    monkeypatch.setattr(messages, "accessible_mailbox", accessible)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(messages.send(
            from_mailbox_id="mailbox-1", to="bob@example.test",
            subject="Hello\\r\\nBcc: evil@example.test", body="Hi",
            user={"sub": "user-1", "tenant_id": "tenant-1"}, s=object(),
        ))
    assert caught.value.status_code == 422

