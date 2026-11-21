import asyncio
import sys
from pathlib import Path

import httpx
import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app import backfill_existing_users


class UnauthorizedKeycloakClient:
    def __init__(self):
        self.calls = 0

    async def post(self, *args, **kwargs):
        self.calls += 1
        request = httpx.Request("POST", "https://keycloak.invalid/realms/master/token")
        return httpx.Response(401, request=request)


def test_admin_token_fails_fast_on_rejected_credentials(monkeypatch):
    client = UnauthorizedKeycloakClient()
    monkeypatch.setattr(backfill_existing_users, "ADMIN_PASSWORD", "test-only-invalid")

    with pytest.raises(RuntimeError, match="HTTP 401"):
        asyncio.run(backfill_existing_users.admin_token(client))

    assert client.calls == 1
