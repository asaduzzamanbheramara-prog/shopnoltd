import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_ROOT = REPO_ROOT / "platform" / "oauth-service"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
if str(REPO_ROOT / "shared" / "libraries" / "python") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "shared" / "libraries" / "python"))

from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.api.users import _find_email_owner, _normalize_email


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


def test_email_normalization_trims_and_lowercases():
    assert _normalize_email("  Alice.Example@Example.COM  ") == "alice.example@example.com"
    assert _normalize_email(None) == ""


def test_email_owner_lookup_is_case_insensitive_and_bounded():
    session = FakeSession([])
    result = asyncio.run(_find_email_owner(session, "alice@example.com"))

    sql = str(
        session.statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert result is None
    assert "lower(users.email) = 'alice@example.com'" in sql
    assert "LIMIT 2" in sql


def test_email_owner_lookup_excludes_the_current_user():
    session = FakeSession([SimpleNamespace(id="another-user")])
    result = asyncio.run(
        _find_email_owner(
            session,
            "alice@example.com",
            exclude_user_id="current-user",
        )
    )

    sql = str(
        session.statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert result.id == "another-user"
    assert "users.id != 'current-user'" in sql


def test_legacy_case_variant_duplicates_fail_closed():
    session = FakeSession(
        [SimpleNamespace(id="legacy-one"), SimpleNamespace(id="legacy-two")]
    )

    try:
        asyncio.run(_find_email_owner(session, "alice@example.com"))
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "administrator reconciliation" in exc.detail
    else:
        raise AssertionError("ambiguous case-insensitive email ownership must fail closed")
