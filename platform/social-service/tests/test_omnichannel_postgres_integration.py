import asyncio
import os
import unittest
from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from fastapi import HTTPException

from app.api import omnichannel as omnichannel_api
from app.services import action_executor


class OmnichannelPostgresIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Real PostgreSQL tests for the API SQL contracts and SKIP LOCKED worker claim."""

    async def asyncSetUp(self):
        database_url = os.environ.get("DATABASE_URL", "")
        if not database_url.startswith("postgresql+asyncpg://"):
            raise RuntimeError("DATABASE_URL must use postgresql+asyncpg for integration tests")
        self.engine = create_async_engine(database_url, pool_size=5, max_overflow=5)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.tenant = "it-" + uuid4().hex[:24]
        self.connection_id = str(uuid4())
        async with self.sessions() as session:
            await session.execute(text("""
                INSERT INTO social_connections
                  (id, tenant_id, platform, account_type, platform_account_id, status)
                VALUES (CAST(:id AS uuid), :tenant, 'telegram', 'bot', :account, 'connected')
            """), {"id": self.connection_id, "tenant": self.tenant, "account": "bot-" + uuid4().hex})
            await session.commit()

    async def asyncTearDown(self):
        async with self.sessions() as session:
            await session.execute(text("DELETE FROM platform_actions WHERE tenant_id=:tenant"), {"tenant": self.tenant})
            await session.execute(text("DELETE FROM social_connections WHERE tenant_id=:tenant"), {"tenant": self.tenant})
            await session.commit()
        await self.engine.dispose()

    def _body(self, key=None, message="integration message"):
        return omnichannel_api.ActionIn(
            platform="telegram",
            action="send_message",
            connection_id=self.connection_id,
            idempotency_key=key or ("idem-" + uuid4().hex),
            target_id="private-test-chat",
            payload={"text": message},
        )

    async def _queue(self, tenant, body=None):
        async with self.sessions() as session:
            return await omnichannel_api.queue_action(
                body or self._body(),
                user={"tenant_id": tenant},
                s=session,
            )

    async def test_concurrent_same_idempotency_key_creates_one_action(self):
        key = "concurrent-" + uuid4().hex
        first, second = await asyncio.gather(
            self._queue(self.tenant, self._body(key, "same payload")),
            self._queue(self.tenant, self._body(key, "same payload")),
        )
        self.assertEqual(first["id"], second["id"])
        async with self.sessions() as session:
            count = (await session.execute(text("""
                SELECT count(*) FROM platform_actions
                WHERE tenant_id=:tenant AND idempotency_key=:key
            """), {"tenant": self.tenant, "key": key})).scalar_one()
        self.assertEqual(count, 1)

    async def test_reused_idempotency_key_with_changed_payload_returns_409(self):
        key = "conflict-" + uuid4().hex
        original = await self._queue(self.tenant, self._body(key, "original"))
        with self.assertRaises(HTTPException) as caught:
            await self._queue(self.tenant, self._body(key, "changed"))
        self.assertEqual(caught.exception.status_code, 409)
        async with self.sessions() as session:
            rows = (await session.execute(text("""
                SELECT id, request_payload FROM platform_actions
                WHERE tenant_id=:tenant AND idempotency_key=:key
            """), {"tenant": self.tenant, "key": key})).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(str(rows[0][0]), str(original["id"]))
        self.assertEqual(rows[0][1], {"text": "original"})

    async def test_approval_is_tenant_scoped_and_audited_once(self):
        action = await self._queue(self.tenant)
        with self.assertRaises(HTTPException) as non_admin:
            async with self.sessions() as session:
                await omnichannel_api.approve_action(
                    action["id"], user={"tenant_id": self.tenant, "roles": ["user"]}, s=session
                )
        self.assertEqual(non_admin.exception.status_code, 403)

        with self.assertRaises(HTTPException) as cross_tenant:
            async with self.sessions() as session:
                await omnichannel_api.approve_action(
                    action["id"], user={"tenant_id": "other-" + uuid4().hex[:20], "roles": ["admin"]}, s=session
                )
        self.assertEqual(cross_tenant.exception.status_code, 404)

        async with self.sessions() as session:
            approved = await omnichannel_api.approve_action(
                action["id"],
                user={"sub": "admin-first", "tenant_id": self.tenant, "roles": ["platform_admin"]},
                s=session,
            )
        self.assertEqual(approved["approval_status"], "approved")
        self.assertEqual(approved["approved_by"], "admin-first")

        async with self.sessions() as session:
            repeated = await omnichannel_api.approve_action(
                action["id"],
                user={"sub": "admin-second", "tenant_id": self.tenant, "roles": ["admin"]},
                s=session,
            )
        self.assertEqual(repeated["approved_by"], "admin-first")

    async def test_terminal_action_cannot_be_newly_approved(self):
        action = await self._queue(self.tenant)
        async with self.sessions() as session:
            await session.execute(text("""
                UPDATE platform_actions SET status='succeeded'
                WHERE tenant_id=:tenant AND id=CAST(:id AS uuid)
            """), {"tenant": self.tenant, "id": action["id"]})
            await session.commit()
        with self.assertRaises(HTTPException) as caught:
            async with self.sessions() as session:
                await omnichannel_api.approve_action(
                    action["id"],
                    user={"sub": "admin", "tenant_id": self.tenant, "roles": ["admin"]},
                    s=session,
                )
        self.assertEqual(caught.exception.status_code, 409)

    async def test_two_workers_claim_distinct_actions_at_most_once(self):
        ids = [str(uuid4()), str(uuid4())]
        async with self.sessions() as session:
            for action_id in ids:
                await session.execute(text("""
                    INSERT INTO platform_actions
                      (id, tenant_id, platform, action, status, approval_status, request_payload)
                    VALUES (CAST(:id AS uuid), :tenant, 'not_implemented', 'send_message',
                            'queued', 'approved', '{}'::jsonb)
                """), {"id": action_id, "tenant": self.tenant})
            await session.commit()

        with patch.object(action_executor, "SessionLocal", self.sessions):
            results = await asyncio.gather(action_executor.process_one(), action_executor.process_one())
        self.assertEqual(results, [True, True])

        async with self.sessions() as session:
            rows = (await session.execute(text("""
                SELECT id::text, status, attempt_count FROM platform_actions
                WHERE tenant_id=:tenant AND id::text = ANY(:ids)
            """), {"tenant": self.tenant, "ids": ids})).all()
        self.assertEqual(len(rows), 2)
        self.assertEqual({row[0] for row in rows}, set(ids))
        self.assertTrue(all(row[1] == "unsupported" and row[2] == 1 for row in rows))


if __name__ == "__main__":
    unittest.main()
