import asyncio
import pytest
from fastapi import HTTPException

from app.api.omnichannel import ActionIn, queue_action


class NoDatabase:
    async def execute(self, *_args, **_kwargs):
        raise AssertionError("database must not be touched while executor is disabled")


def test_queue_action_rejects_requests_when_executor_is_disabled(monkeypatch):
    monkeypatch.setattr("app.api.omnichannel.settings.omnichannel_executor_enabled", False)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(queue_action(
            ActionIn(platform="gmail", action="send_message", approved=True),
            user={"sub": "user-123", "tenant_id": "tenant-1"},
            s=NoDatabase(),
        ))

    assert exc.value.status_code == 503
    assert "no action was queued" in exc.value.detail

def test_provider_status_exposes_executor_readiness(monkeypatch):
    from app.api.omnichannel import provider_status

    monkeypatch.setattr("app.api.omnichannel.settings.omnichannel_executor_enabled", False)
    providers = asyncio.run(provider_status(user={"sub": "user-123"}))

    assert providers
    assert all(provider["executor_enabled"] is False for provider in providers)
