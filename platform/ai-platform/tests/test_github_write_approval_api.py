"""Behavior tests for the GitHub write approval API handlers.

The database and GitHub HTTP client are deterministic fakes: these tests exercise
the actual async route functions without requiring PostgreSQL, Keycloak, or a
real GitHub credential.
"""
import asyncio
import unittest
from datetime import datetime, timedelta, timezone
import uuid
from unittest.mock import patch

from fastapi import HTTPException

from app.api import connections


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDB:
    def __init__(self, connection, consumed_id=None):
        self.connection = connection
        self.consumed_id = consumed_id
        self.added = []
        self.execute_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0

    async def execute(self, statement):
        self.execute_calls += 1
        # First statement is _owned(SELECT); second is the conditional UPDATE.
        if self.execute_calls == 1:
            return _Result(self.connection)
        return _Result(self.consumed_id)

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, value):
        if value.id is None:
            value.id = uuid.uuid4()

    async def rollback(self):
        self.rollback_calls += 1


class _FakeGitHubResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "commit": {"sha": "test-commit-sha"},
            "content": {"path": "docs/approved.md"},
        }


class _FakeGitHubClient:
    def __init__(self):
        self.put_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def put(self, url, **kwargs):
        self.put_calls.append((url, kwargs))
        return _FakeGitHubResponse()


class GitHubWriteApprovalApiTests(unittest.TestCase):
    def setUp(self):
        self.connection_id = uuid.uuid4()
        self.user = {"sub": "admin-user-1", "roles": ["admin"]}
        self.connection = connections.AIConnection(
            id=self.connection_id,
            user_id=self.user["sub"],
            kind="github",
            name="test connection",
            secret_encrypted="encrypted-test-token",
        )
        self.operation = {
            "repo": "owner/repo",
            "path": "docs/approved.md",
            "content": "approved content",
            "message": "Add approved file",
            "branch": "main",
            "sha": None,
        }

    def _approval_request(self):
        return connections.GithubWriteApprovalRequest(**self.operation)

    def test_approval_handler_persists_user_connection_digest_and_expiry(self):
        async def run():
            db = _FakeDB(self.connection)
            started = datetime.now(timezone.utc)
            result = await connections.approve_github_write(
                self.connection_id, self._approval_request(), self.user, db
            )

            self.assertEqual(len(db.added), 1)
            approval = db.added[0]
            self.assertIsInstance(approval, connections.GitHubWriteApproval)
            self.assertEqual(approval.connection_id, self.connection_id)
            self.assertEqual(approval.user_id, self.user["sub"])
            self.assertEqual(
                approval.operation_hash,
                connections._github_write_digest(self._approval_request()),
            )
            self.assertGreater(approval.expires_at, started)
            self.assertLessEqual(approval.expires_at, started + timedelta(minutes=5, seconds=2))
            self.assertEqual(result["approval_id"], str(approval.id))
            self.assertTrue(result["single_use"])
            self.assertEqual(db.commit_calls, 1)

        asyncio.run(run())

    def test_write_handler_consumes_approval_before_github_put(self):
        async def run():
            approval_id = uuid.uuid4()
            db = _FakeDB(self.connection, consumed_id=approval_id)
            body = connections.GithubWrite(
                **self.operation, approval_id=approval_id
            )
            client = _FakeGitHubClient()

            with patch.object(connections, "decrypt_secret", return_value="test-token"), patch.object(
                connections.httpx, "AsyncClient", return_value=client
            ):
                result = await connections.github_write_file(
                    self.connection_id, body, self.user, db
                )

            self.assertEqual(db.commit_calls, 1)
            self.assertEqual(len(client.put_calls), 1)
            self.assertEqual(result["commit"], "test-commit-sha")
            self.assertEqual(result["content"], "docs/approved.md")
            _, request = client.put_calls[0]
            self.assertEqual(request["json"]["branch"], "main")
            self.assertEqual(request["headers"]["Authorization"], "Bearer test-token")

        asyncio.run(run())

    def test_missing_or_reused_approval_fails_closed_without_github_call(self):
        async def run():
            db = _FakeDB(self.connection, consumed_id=None)
            approval_id = uuid.uuid4()
            body = connections.GithubWrite(
                **self.operation, approval_id=approval_id
            )
            client = _FakeGitHubClient()

            with patch.object(connections, "decrypt_secret", return_value="test-token"), patch.object(
                connections.httpx, "AsyncClient", return_value=client
            ):
                with self.assertRaises(HTTPException) as raised:
                    await connections.github_write_file(
                        self.connection_id, body, self.user, db
                    )

            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(db.rollback_calls, 1)
            self.assertEqual(client.put_calls, [])

        asyncio.run(run())

    def test_modified_operation_has_a_different_digest(self):
        original = self._approval_request()
        modified = connections.GithubWriteApprovalRequest(
            **{**self.operation, "content": "changed after approval"}
        )
        self.assertNotEqual(
            connections._github_write_digest(original),
            connections._github_write_digest(modified),
        )


if __name__ == "__main__":
    unittest.main()
