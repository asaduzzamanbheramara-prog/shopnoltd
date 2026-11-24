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
        self.assertEqual(store.health(), "postgres")

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

        self.assertEqual(loaded["wallets"]["w1"]["balance"], 5)
        self.assertGreaterEqual(cursor.execute.call_count, 3)

    def test_middleware_returns_response_when_persistence_save_fails(self):
        import app_platform.api.main as main

        original_store = main.state_store
        failing_store = MagicMock(enabled=True)
        failing_store.save.side_effect = RuntimeError("temporary database outage")
        main.state_store = failing_store

        async def call_next(_request):
            return object()

        try:
            response = asyncio.run(main.persist_state_after_request(object(), call_next))
        finally:
            main.state_store = original_store

        self.assertIsNotNone(response)
        failing_store.save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
