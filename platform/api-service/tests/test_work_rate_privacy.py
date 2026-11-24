import asyncio
from types import SimpleNamespace

from app.api.v3_work import config_dict, get_task_rates, worker_rate_payload


def test_worker_config_hides_internal_platform_rates():
    config = SimpleNamespace(
        id=1,
        work_id="work-1",
        task_url="https://example.test/task",
        media_url=None,
        media_type="none",
        required_watch_seconds=30,
        watch_rate_per_minute=4,
        rate_currency="USD",
        rate_rules='[{"from_second":0,"rate_per_minute":4}]',
        social_rates='{"like":"0.25"}',
    )
    result = config_dict(config)
    assert result["task_url"] == "https://example.test/task"
    assert result["required_watch_seconds"] == 30
    assert "watch_rate_per_minute" not in result
    assert "rate_rules" not in result
    assert "social_rates" not in result


def test_task_creator_config_can_inspect_own_rates():
    config = SimpleNamespace(
        id=1,
        work_id="work-1",
        task_url="https://example.test/task",
        media_url=None,
        media_type="none",
        required_watch_seconds=30,
        watch_rate_per_minute=4,
        rate_currency="USD",
        rate_rules='[{"from_second":0,"rate_per_minute":4}]',
        social_rates='{"like":"0.25"}',
    )
    result = config_dict(config, include_admin_rates=True)
    assert result["watch_rate_per_minute"] == "4"
    assert result["rate_rules"][0]["rate_per_minute"] == 4
    assert result["social_rates"]["like"] == "0.25"


def test_global_platform_rate_registry_is_not_visible_to_workers():
    result = asyncio.run(get_task_rates(None, {"sub": "ordinary-worker"}))
    assert result == {"supported_currencies": [], "platforms": [], "rates": {}}


def test_worker_receives_only_effective_task_rate_not_platform_identity():
    work = SimpleNamespace(task_type="like", reward_amount="0.10", currency="USD")
    global_rate = SimpleNamespace(rate="0.25", currency="USD", platform="instagram")
    result = worker_rate_payload(work, None, global_rate)
    assert result == {
        "worker_rate": "0.25",
        "worker_rate_unit": "per_task",
        "rate_currency": "USD",
    }
    assert "platform" not in result


def test_watch_worker_receives_per_minute_rate_only():
    work = SimpleNamespace(task_type="watch", reward_amount="0", currency="USD")
    config = SimpleNamespace(watch_rate_per_minute="0.50", rate_currency="USD")
    result = worker_rate_payload(work, config)
    assert result == {
        "worker_rate": "0.50",
        "worker_rate_unit": "per_minute",
        "rate_currency": "USD",
    }


from datetime import datetime
from decimal import Decimal

from app.api.v2 import work_dict
from app.api.v3_work import session_dict


def test_new_work_exposes_only_worker_net_reward_to_non_creator():
    work = SimpleNamespace(
        id="work-70-30", tenant_id="default", creator_id="creator-1",
        title="Follow", description="Follow the page", requirements=None,
        reference_image=None, before_post_screenshot=None, task_type="follow",
        platform="instagram", reward_amount=Decimal("10.00"),
        payout_share_percent=70, currency="USD", max_workers=5,
        deadline=None, status="open", created_at=datetime(2026, 1, 1),
    )
    worker_view = work_dict(work, viewer_id="worker-1")
    assert worker_view["reward_amount"] == "7.00000000"
    assert worker_view["total_amount"] == "35.00000000"
    assert "platform_share_percent" not in worker_view
    assert "gross_reward_amount" not in worker_view


def test_creator_can_see_gross_budget_and_split_configuration():
    work = SimpleNamespace(
        id="work-70-30", tenant_id="default", creator_id="creator-1",
        title="Follow", description="Follow the page", requirements=None,
        reference_image=None, before_post_screenshot=None, task_type="follow",
        platform="instagram", reward_amount=Decimal("10.00"),
        payout_share_percent=70, currency="USD", max_workers=5,
        deadline=None, status="open", created_at=datetime(2026, 1, 1),
    )
    creator_view = work_dict(work, viewer_id="creator-1")
    assert creator_view["reward_amount"] == "10.00"
    assert creator_view["gross_reward_amount"] == "10.00"
    assert creator_view["worker_share_percent"] == 70
    assert creator_view["platform_share_percent"] == 30


def test_session_amount_is_worker_net_not_gross():
    session = SimpleNamespace(
        id="session-1", work_id="work-1", worker_id="worker-1", stage="finished",
        started_at=None, ended_at=None, work_seconds=60, watch_seconds=60,
        interaction_seconds=5, eligible_watch_seconds=60,
        calculated_amount=Decimal("10.00"), payout_share_percent=70, currency="USD",
    )
    assert session_dict(session)["calculated_amount"] == "7.00000000"


def test_new_work_worker_rate_shows_70_percent_without_platform_identity():
    work = SimpleNamespace(task_type="like", reward_amount="0.25", currency="USD", payout_share_percent=70)
    global_rate = SimpleNamespace(rate="0.25", currency="USD", platform="instagram")
    result = worker_rate_payload(work, None, global_rate)
    assert result == {
        "worker_rate": "0.175",
        "worker_rate_unit": "per_task",
        "rate_currency": "USD",
    }
    assert "platform" not in result
