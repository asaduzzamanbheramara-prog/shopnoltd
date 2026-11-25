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
