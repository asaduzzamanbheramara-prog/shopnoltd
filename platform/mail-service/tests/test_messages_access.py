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
