from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from app.api.v2 import can_view_work, is_admin_user, work_dict


def make_work(**overrides):
    values = dict(
        id="work-1", tenant_id="tenant-1", creator_id="creator-1", title="Test task",
        description="Complete a task", requirements="Proof required", reference_image="data:image/png;base64,abc",
        before_post_screenshot="data:image/png;base64,private", task_type="simple", platform="shopnoltd",
        reward_amount=Decimal("10"), payout_share_percent=70, currency="BDT", max_workers=3,
        deadline=None, status="open", created_at=datetime(2026, 1, 1),
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_worker_dto_hides_creator_tenant_and_private_pre_post_evidence():
    payload = work_dict(make_work(), viewer_id="worker-1")
    assert "creator_id" not in payload
    assert "tenant_id" not in payload
    assert "before_post_screenshot" not in payload
    assert payload["reward_amount"] == "7.00000000"


def test_creator_can_see_own_private_evidence_but_not_tenant_identity():
    payload = work_dict(make_work(), viewer_id="creator-1")
    assert payload["before_post_screenshot"] == "data:image/png;base64,private"
    assert "creator_id" not in payload
    assert "tenant_id" not in payload


def test_admin_can_see_moderation_metadata():
    payload = work_dict(make_work(), viewer_id="admin-1", include_admin_fields=True)
    assert payload["creator_id"] == "creator-1"
    assert payload["tenant_id"] == "tenant-1"
    assert payload["before_post_screenshot"] == "data:image/png;base64,private"


def test_ordinary_users_cannot_view_other_users_drafts_or_pending_review():
    user = {"sub": "worker-1", "tenant_id": "tenant-1"}
    assert not can_view_work(make_work(status="draft"), user)
    assert not can_view_work(make_work(status="pending_review"), user)
    assert can_view_work(make_work(status="open"), user)


def test_creator_and_admin_can_view_drafts():
    creator = {"sub": "creator-1", "tenant_id": "tenant-1"}
    admin = {"sub": "admin-1", "tenant_id": "tenant-1", "roles": ["platform_admin"]}
    assert can_view_work(make_work(status="draft"), creator)
    assert can_view_work(make_work(status="draft"), admin)
    assert is_admin_user(admin)


def test_other_tenant_cannot_view_work_even_if_admin():
    admin = {"sub": "admin-1", "tenant_id": "tenant-2", "roles": ["admin"]}
    assert not can_view_work(make_work(status="open"), admin)


def test_completed_assignments_consume_capacity():
    from app.api.v2 import remaining_work_slots

    assert remaining_work_slots(3, 1, 2) == 0
    assert remaining_work_slots(3, 1, 1) == 1
    assert remaining_work_slots(1, 0, 1) == 0
    assert remaining_work_slots(2, 0, 0) == 2
