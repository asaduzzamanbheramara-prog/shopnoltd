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
