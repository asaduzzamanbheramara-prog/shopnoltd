import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_ROOT = REPO_ROOT / "platform" / "oauth-service"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
if str(REPO_ROOT / "shared" / "libraries" / "python") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "shared" / "libraries" / "python"))

from app.api import users


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return FakeResult(self.rows)


def test_status_is_scoped_to_authenticated_subject_and_redacts_provider_errors(monkeypatch):
    now = datetime(2026, 10, 15, tzinfo=timezone.utc)
    jobs = [
        SimpleNamespace(
            resource_type="mailbox",
            status="failed",
            attempts=3,
            created_at=now,
            updated_at=now,
            last_error="https://internal-provider.invalid token=secret",
        ),
        SimpleNamespace(
            resource_type="subdomain",
            status="pending",
            attempts=0,
            created_at=now,
            updated_at=now,
            last_error=None,
        ),
    ]
    session = FakeSession(jobs)
    monkeypatch.setattr(users, "verify_token", AsyncMock(return_value={"sub": "only-this-user"}))

    result = asyncio.run(
        users.my_provisioning_status(
            creds=SimpleNamespace(credentials="signed-user-token"),
            s=session,
        )
    )

    sql = str(session.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "account_provisioning_jobs.keycloak_id = 'only-this-user'" in sql
    assert result["status"] == "ok"
    assert [item["resource_type"] for item in result["provisioning"]] == ["mailbox", "subdomain"]
    failed = result["provisioning"][0]
    assert failed["status"] == "failed"
    assert failed["attempts"] == 3
    assert failed["message"] == "Provisioning failed; contact support."
    assert "internal-provider" not in str(result)
    assert "secret" not in str(result)


def test_status_rejects_token_without_subject(monkeypatch):
    monkeypatch.setattr(users, "verify_token", AsyncMock(return_value={"email": "user@example.test"}))
    from fastapi import HTTPException

    try:
        asyncio.run(
            users.my_provisioning_status(
                creds=SimpleNamespace(credentials="signed-user-token"),
                s=FakeSession([]),
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("missing subject must be rejected")
