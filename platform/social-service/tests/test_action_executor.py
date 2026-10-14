import unittest
from unittest.mock import AsyncMock, patch

from fastapi.security import HTTPAuthorizationCredentials

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

    async def execute(self, statement, params):
        self.calls.append((str(statement), params))
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
