import unittest
from unittest.mock import AsyncMock, patch

from fastapi.security import HTTPAuthorizationCredentials

from app.services import action_executor
from app.services.action_executor import telegram_message_payload
from app.api import omnichannel_oauth


class TelegramPayloadTests(unittest.TestCase):
    def test_telegram_payload_uses_target_and_text(self):
        self.assertEqual(
            telegram_message_payload("send_message", {"text": "hello"}, "chat-123"),
            {"chat_id": "chat-123", "text": "hello"},
        )

    def test_telegram_payload_accepts_payload_chat_id(self):
        self.assertEqual(
            telegram_message_payload("send_message", {"chat_id": "chat-1", "message": "hello"}, None),
            {"chat_id": "chat-1", "text": "hello"},
        )

    def test_unsupported_or_invalid_actions_fail_closed(self):
        cases = [
            ("like", {"text": "hello"}, "chat-1"),
            ("create_post", {"text": "hello"}, "chat-1"),
            ("send_message", {}, "chat-1"),
            ("send_message", {"text": "hello"}, None),
            ("send_message", {"text": "x" * 4097}, "chat-1"),
        ]
        for action, payload, target in cases:
            with self.subTest(action=action, payload_keys=list(payload)):
                with self.assertRaises(ValueError):
                    telegram_message_payload(action, payload, target)


if __name__ == "__main__":
    unittest.main()


class _FakeTelegramResponse:
    status_code = 200

    @staticmethod
    def json():
        return {"ok": True, "result": {"id": 123456, "is_bot": True, "username": "shopno_test_bot", "first_name": "Shopno Test"}}


class _FakeTelegramClient:
    def __init__(self, *args, **kwargs):
        self.options = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        self.url = url
        return _FakeTelegramResponse()


class _FakeDBResult:
    def __init__(self, token_id=None, row=None):
        self.token_id = token_id
        self.row = row

    def scalar_one(self):
        return self.token_id

    def mappings(self):
        return self

    def one(self):
        return self.row


class _FakeSession:
    def __init__(self):
        self.calls = []
        self.results = [
            _FakeDBResult(token_id="telegram-token-row-id"),
            _FakeDBResult(row={
                "id": "telegram-connection-id",
                "platform": "telegram",
                "account_type": "bot",
                "platform_account_id": "123456",
                "username": "shopno_test_bot",
                "display_name": "Shopno Test",
                "status": "connected",
                "scopes": [],
                "token_expires_at": None,
                "metadata": {"provider": "telegram", "account_type": "bot"},
                "connected_at": None,
                "last_sync_at": None,
            }),
        ]

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return self.results[len(self.calls) - 1]

    async def commit(self):
        return None


class _FakeSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class TelegramConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_bot_token_is_validated_encrypted_and_never_returned(self):
        token = "test-telegram-bot-token-" + ("x" * 30)
        session = _FakeSession()

        class FakeCipher:
            @staticmethod
            def encrypt(value):
                return b"encrypted:" + value

        with (
            patch.object(omnichannel_oauth, "verify_token", new=AsyncMock(return_value={
                "sub": "user-1", "tenant_id": "tenant-1"
            })),
            patch.object(omnichannel_oauth, "_fernet", return_value=FakeCipher()),
            patch.object(omnichannel_oauth, "SessionLocal", return_value=_FakeSessionContext(session)),
            patch.object(omnichannel_oauth.httpx, "AsyncClient", _FakeTelegramClient),
        ):
            result = await omnichannel_oauth.connect_telegram_bot(
                omnichannel_oauth.TelegramBotConnectIn(bot_token=token),
                HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-jwt"),
            )

        self.assertEqual(result["platform_account_id"], "123456")
        self.assertEqual(session.calls[0][1]["encrypted"], ("encrypted:" + token))
        self.assertEqual(session.calls[0][1]["tenant"], "tenant-1")
        self.assertEqual(session.calls[1][1]["token_ref"], "telegram-token-row-id")
        self.assertNotIn(token, repr(result))
        self.assertNotIn(token, repr(session.calls[0][1]["metadata"]))


class _FakeExecutionResult:
    def __init__(self, mapping=None, scalar=None):
        self.mapping = mapping
        self.scalar = scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self.mapping

    def scalar_one_or_none(self):
        return self.scalar


class _FakeExecutionSession:
    def __init__(self, provider_status=200):
        self.calls = []
        self.commits = 0
        self.provider_status = provider_status
        self.results = [
            _FakeExecutionResult(),
            _FakeExecutionResult(mapping={
                "id": "action-1", "tenant_id": "tenant-a", "connection_id": "connection-a",
                "platform": "telegram", "action": "send_message", "target_id": "chat-42",
                "request_payload": {"text": "safe test"}, "attempt_count": 1,
            }),
            _FakeExecutionResult(mapping={
                "status": "connected", "platform": "telegram", "platform_account_id": "bot-42",
                "access_token_ref": "token-row-42",
            }),
            _FakeExecutionResult(scalar="supported"),
            _FakeExecutionResult(mapping={"encrypted_access_token": "encrypted-token"}),
            _FakeExecutionResult(),
        ]

    async def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return self.results[len(self.calls) - 1]

    async def commit(self):
        self.commits += 1


class _FakeTelegramSendResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    @staticmethod
    def json():
        return {
            "ok": True,
            "parameters": {"retry_after": 3},
            "result": {"message_id": 9001, "chat": {"id": 42}},
        }


class _FakeTelegramSendClient:
    response_status = 200
    last_request = None

    def __init__(self, *args, **kwargs):
        self.options = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json):
        type(self).last_request = {"url": url, "json": json}
        return _FakeTelegramSendResponse(type(self).response_status)


class _FakeExecutionSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class TelegramExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def _run(self, provider_status):
        session = _FakeExecutionSession(provider_status=provider_status)
        _FakeTelegramSendClient.response_status = provider_status
        class FakeCipher:
            @staticmethod
            def decrypt(value):
                return b"tenant-bound-bot-token"

        with (
            patch.object(action_executor, "SessionLocal", return_value=_FakeExecutionSessionContext(session)),
            patch.object(action_executor.httpx, "AsyncClient", _FakeTelegramSendClient),
            patch.object(omnichannel_oauth, "_fernet", return_value=FakeCipher()),
        ):
            processed = await action_executor.process_one()
        return processed, session

    async def test_success_uses_tenant_bound_credential_and_persists_provider_ids(self):
        processed, session = await self._run(200)
        self.assertTrue(processed)
        self.assertIn("tenant_id=:tenant", session.calls[2][0])
        self.assertEqual(session.calls[2][1]["tenant"], "tenant-a")
        self.assertEqual(session.calls[3][1], {"platform": "telegram", "action": "send_message"})
        self.assertEqual(_FakeTelegramSendClient.last_request["json"], {"chat_id": "chat-42", "text": "safe test"})
        self.assertIn("tenant-bound-bot-token", _FakeTelegramSendClient.last_request["url"])
        finish_params = session.calls[-1][1]
        self.assertEqual(finish_params["status"], "succeeded")
        self.assertIn('"provider_message_id": 9001', finish_params["result"])
        self.assertIn('"provider_chat_id": 42', finish_params["result"])

    async def test_explicit_429_is_scheduled_for_bounded_retry(self):
        processed, session = await self._run(429)
        self.assertTrue(processed)
        finish_params = session.calls[-1][1]
        self.assertEqual(finish_params["status"], "retry_wait")
        self.assertEqual(finish_params["delay"], 3)
        self.assertEqual(finish_params["code"], "provider_rate_limited")
