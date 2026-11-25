import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch


class StateStoreTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("DATABASE_URL", None)

    def test_disabled_mode_is_memory_and_noops(self):
        from app_platform.api.state_store import PostgresStateStore

        store = PostgresStateStore()
        self.assertFalse(store.enabled)
        self.assertEqual(store.health(), "memory")
        self.assertEqual(store.load(["wallets"]), {})
        store.initialize()
        store.save({"wallets": {"w1": {"balance": 10}}})

    def test_serialize_state_round_trips_unicode_and_json_values(self):
        from app_platform.api.state_store import serialize_state

        state = {"users": {"u1": {"name": "আসাদ", "active": True}}}
        encoded = serialize_state(state)
        self.assertEqual(encoded, state)
        self.assertIsNot(encoded, state)

    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://example.invalid/shopnoltd"})
    def test_initialize_load_and_save_use_postgres_contract(self):
        from app_platform.api.state_store import PostgresStateStore

        store = PostgresStateStore()
        self.assertTrue(store.enabled)

        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            {"state_key": "wallets", "state_value": {"w1": {"balance": 5}}}
        ]
        connection.__enter__.return_value = connection

        with patch.object(store, "_connect", return_value=connection):
            store.initialize()
            loaded = store.load(["wallets"])
            store.save({"wallets": {"w1": {"balance": 5}}})
            self.assertEqual(store.health(), "postgres")

        self.assertEqual(loaded["wallets"]["w1"]["balance"], 5)
        self.assertGreaterEqual(cursor.execute.call_count, 3)

    def test_middleware_rejects_writes_without_durable_storage(self):
        import app_platform.api.main as main

        original_store = main.state_store
        main.state_store = MagicMock(enabled=False)
        request = MagicMock(method="POST")

        async def call_next(_request):
            self.fail("write must be blocked before the route executes")

        try:
            response = asyncio.run(main.persist_state_after_request(request, call_next))
        finally:
            main.state_store = original_store

        self.assertEqual(response.status_code, 503)

    def test_middleware_rolls_back_memory_and_returns_503_when_save_fails(self):
        import app_platform.api.main as main
        from starlette.responses import JSONResponse

        original_store = main.state_store
        original_wallets = dict(main.wallets_db)
        main.wallets_db.clear()
        main.wallets_db["before"] = {"balance": 10}
        failing_store = MagicMock(enabled=True)
        failing_store.save.side_effect = RuntimeError("temporary database outage")
        main.state_store = failing_store
        request = MagicMock(method="POST")

        async def call_next(_request):
            main.wallets_db["after"] = {"balance": 999}
            return JSONResponse({"ok": True})

        try:
            response = asyncio.run(main.persist_state_after_request(request, call_next))
        finally:
            main.state_store = original_store
            main.wallets_db.clear()
            main.wallets_db.update(original_wallets)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(main.wallets_db, original_wallets)
        failing_store.save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
