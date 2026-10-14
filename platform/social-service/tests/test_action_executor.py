import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.services import action_executor
from app.services.action_executor import telegram_message_payload
from app.api import omnichannel as omnichannel_api
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


    async def test_invalid_token_length_is_not_reflected_or_sent_to_provider(self):
        token = "short-secret-token"
        with (
            patch.object(omnichannel_oauth, "verify_token", new=AsyncMock(return_value={
                "sub": "user-1", "tenant_id": "tenant-1"
            })),
            patch.object(omnichannel_oauth.httpx, "AsyncClient") as client,
        ):
            with self.assertRaises(HTTPException) as caught:
                await omnichannel_oauth.connect_telegram_bot(
                    omnichannel_oauth.TelegramBotConnectIn(bot_token=token),
                    HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-jwt"),
                )
        self.assertEqual(caught.exception.status_code, 400)
        self.assertNotIn(token, str(caught.exception))
        client.assert_not_called()


    async def test_network_error_does_not_expose_token_url_in_http_exception(self):
        token = "valid-shaped-test-token-" + ("x" * 30)

        class FakeCipher:
            @staticmethod
            def encrypt(value):
                return b"encrypted"

        class FailingTelegramClient:
            def __init__(self, *args, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc, tb):
                return False
            async def get(self, url):
                raise omnichannel_oauth.httpx.NetworkError("request failed for " + url)

        with (
            patch.object(omnichannel_oauth, "verify_token", new=AsyncMock(return_value={
                "sub": "user-1", "tenant_id": "tenant-1"
            })),
            patch.object(omnichannel_oauth, "_fernet", return_value=FakeCipher()),
            patch.object(omnichannel_oauth.httpx, "AsyncClient", FailingTelegramClient),
        ):
            with self.assertRaises(HTTPException) as caught:
                await omnichannel_oauth.connect_telegram_bot(
                    omnichannel_oauth.TelegramBotConnectIn(bot_token=token),
                    HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-jwt"),
                )

        self.assertEqual(caught.exception.status_code, 502)
        self.assertNotIn(token, str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)



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
    def __init__(self, provider_status=200, attempt_count=1):
        self.calls = []
        self.commits = 0
        self.provider_status = provider_status
        self.results = [
            _FakeExecutionResult(),
            _FakeExecutionResult(mapping={
                "id": "action-1", "tenant_id": "tenant-a", "connection_id": "connection-a",
                "platform": "telegram", "action": "send_message", "target_id": "chat-42",
                "request_payload": {"text": "safe test"}, "attempt_count": attempt_count,
            }),
            _FakeExecutionResult(mapping={
                "status": "connected", "platform": "telegram", "platform_account_id": "bot-42",
                "access_token_ref": "token-row-42",
            }),
            _FakeExecutionResult(scalar="supported"),
            _FakeExecutionResult(mapping={"encrypted_access_token": "encrypted-token"}),
            _FakeExecutionResult(),
        ]

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
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
    async def _run(self, provider_status, connection_row=None, capability="supported", attempt_count=1):
        session = _FakeExecutionSession(provider_status=provider_status, attempt_count=attempt_count)
        if connection_row is not None:
            session.results[2] = _FakeExecutionResult(mapping=connection_row)
        if capability != "supported":
            session.results[3] = _FakeExecutionResult(scalar=capability)
        _FakeTelegramSendClient.response_status = provider_status
        _FakeTelegramSendClient.last_request = None
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


    async def test_unapproved_action_is_not_claimed_or_sent(self):
        session = _FakeExecutionSession()
        session.results[1] = _FakeExecutionResult(mapping=None)
        _FakeTelegramSendClient.last_request = None
        with patch.object(action_executor, "SessionLocal", return_value=_FakeExecutionSessionContext(session)):
            processed = await action_executor.process_one()
        self.assertFalse(processed)
        self.assertIn("approval_status='approved'", session.calls[1][0])
        self.assertIsNone(_FakeTelegramSendClient.last_request)

    async def test_success_uses_tenant_bound_credential_and_persists_provider_ids(self):
        processed, session = await self._run(200)
        self.assertTrue(processed)
        self.assertIn("tenant_id=:tenant", session.calls[2][0])
        self.assertIn("approval_status='approved'", session.calls[1][0])
        self.assertEqual(session.calls[2][1]["tenant"], "tenant-a")
        self.assertEqual(session.calls[3][1], {"platform": "telegram", "action": "send_message"})
        self.assertEqual(_FakeTelegramSendClient.last_request["json"], {"chat_id": "chat-42", "text": "safe test"})
        self.assertIn("tenant-bound-bot-token", _FakeTelegramSendClient.last_request["url"])
        finish_params = session.calls[-1][1]
        self.assertEqual(finish_params["status"], "succeeded")
        self.assertIn('"provider_message_id": 9001', finish_params["result"])
        self.assertIn('"provider_chat_id": 42', finish_params["result"])

    async def test_malformed_success_response_never_claims_delivery(self):
        with patch.object(_FakeTelegramSendResponse, "json", return_value={"ok": True, "result": {}}):
            processed, session = await self._run(200)
        self.assertTrue(processed)
        finish_params = session.calls[-1][1]
        self.assertEqual(finish_params["status"], "needs_review")
        self.assertEqual(finish_params["code"], "provider_result_unverified")
        self.assertNotIn('"provider_message_id"', finish_params["result"])

    async def test_explicit_429_is_scheduled_for_bounded_retry(self):
        processed, session = await self._run(429)
        self.assertTrue(processed)
        finish_params = session.calls[-1][1]
        self.assertEqual(finish_params["status"], "retry_wait")
        self.assertEqual(finish_params["delay"], 3)
        self.assertEqual(finish_params["code"], "provider_rate_limited")


    async def test_missing_tenant_owned_connection_fails_without_provider_request(self):
        processed, session = await self._run(200, connection_row={})
        self.assertTrue(processed)
        self.assertIsNone(_FakeTelegramSendClient.last_request)
        finish_params = session.calls[-1][1]
        self.assertEqual(finish_params["status"], "failed")
        self.assertEqual(finish_params["code"], "connection_not_ready")

    async def test_unverified_capability_fails_closed(self):
        processed, session = await self._run(200, capability="provider_dependent")
        self.assertTrue(processed)
        self.assertIsNone(_FakeTelegramSendClient.last_request)
        finish_params = session.calls[-1][1]
        self.assertEqual(finish_params["status"], "unsupported")
        self.assertEqual(finish_params["code"], "capability_not_verified")


    async def test_provider_401_is_terminal_failure(self):
        processed, session = await self._run(401)
        self.assertTrue(processed)
        finish_params = session.calls[-1][1]
        self.assertEqual(finish_params["status"], "failed")
        self.assertEqual(finish_params["code"], "provider_rejected")
        self.assertIn("HTTP 401", finish_params["message"])

    async def test_429_after_retry_budget_is_terminal_rate_limit_failure(self):
        processed, session = await self._run(429, attempt_count=3)
        self.assertTrue(processed)
        finish_params = session.calls[-1][1]
        self.assertEqual(finish_params["status"], "failed")
        self.assertEqual(finish_params["code"], "provider_rate_limit_exhausted")

    async def test_provider_403_is_terminal_failure(self):
        processed, session = await self._run(403)
        self.assertTrue(processed)
        finish_params = session.calls[-1][1]
        self.assertEqual(finish_params["status"], "failed")
        self.assertEqual(finish_params["code"], "provider_rejected")
        self.assertIn("HTTP 403", finish_params["message"])

    async def test_provider_5xx_stops_for_manual_reconciliation(self):
        processed, session = await self._run(503)
        self.assertTrue(processed)
        finish_params = session.calls[-1][1]
        self.assertEqual(finish_params["status"], "needs_review")
        self.assertEqual(finish_params["code"], "provider_result_unknown")
        self.assertNotIn("retry_after", finish_params)



class _QueueResult:
    def __init__(self, scalar=None, row=None):
        self.scalar = scalar
        self.row = row

    def scalar_one_or_none(self):
        return self.scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self.row


class _QueueSession:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []
        self.commits = 0

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return self.results.pop(0)

    async def commit(self):
        self.commits += 1


class ActionQueueIdempotencyTests(unittest.IsolatedAsyncioTestCase):
    def _existing(self, payload):
        return {
            "id": "existing-action-id", "status": "queued", "approval_status": "pending", "platform": "telegram",
            "action": "send_message", "connection_id": None, "client_id": None,
            "target_type": None, "target_id": None, "request_payload": payload,
            "created_at": "2026-10-14T10:00:00Z",
        }


    async def test_unimplemented_provider_adapter_is_rejected_before_queueing(self):
        session = _QueueSession([_QueueResult(scalar="supported")])
        with self.assertRaises(HTTPException) as caught:
            await omnichannel_api.queue_action(
                omnichannel_api.ActionIn(platform="gmail", action="send_message", payload={"text": "hello"}),
                user={"tenant_id": "tenant-1"}, s=session,
            )
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn("provider adapter not implemented", str(caught.exception.detail))
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.commits, 0)

    async def test_provider_dependent_action_is_rejected_before_queueing(self):
        session = _QueueSession([_QueueResult(scalar="provider_dependent")])
        with self.assertRaises(HTTPException) as caught:
            await omnichannel_api.queue_action(
                omnichannel_api.ActionIn(platform="facebook", action="create_post", payload={"text": "hello"}),
                user={"tenant_id": "tenant-1"}, s=session,
            )
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn("provider_dependent", str(caught.exception.detail))
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.commits, 0)

    async def test_same_idempotency_key_and_request_returns_existing_action(self):
        session = _QueueSession([
            _QueueResult(scalar="supported"),
            _QueueResult(row=None),
            _QueueResult(row=self._existing({"text": "hello"})),
        ])
        result = await omnichannel_api.queue_action(
            omnichannel_api.ActionIn(
                platform="telegram", action="send_message",
                idempotency_key="stable-key-1", payload={"text": "hello"},
            ),
            user={"tenant_id": "tenant-1"}, s=session,
        )
        self.assertEqual(result["id"], "existing-action-id")
        self.assertEqual(result["status"], "queued")
        self.assertEqual(session.commits, 1)

    async def test_reused_idempotency_key_with_different_payload_returns_409(self):
        session = _QueueSession([
            _QueueResult(scalar="supported"),
            _QueueResult(row=None),
            _QueueResult(row=self._existing({"text": "original"})),
        ])
        with self.assertRaises(HTTPException) as caught:
            await omnichannel_api.queue_action(
                omnichannel_api.ActionIn(
                    platform="telegram", action="send_message",
                    idempotency_key="stable-key-1", payload={"text": "different"},
                ),
                user={"tenant_id": "tenant-1"}, s=session,
            )
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn("idempotency key", str(caught.exception.detail))
        self.assertEqual(session.commits, 0)



class ActionApprovalTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_admin_cannot_approve_action(self):
        session = _QueueSession([])
        with self.assertRaises(HTTPException) as caught:
            await omnichannel_api.approve_action(
                "action-id", user={"tenant_id": "tenant-1", "roles": ["user"]}, s=session
            )
        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(session.calls, [])

    async def test_admin_approval_is_tenant_scoped_and_audited(self):
        row = {
            "id": "action-id", "status": "queued", "approval_status": "approved",
            "approved_by": "admin-1", "approved_at": "2026-10-14T10:00:00Z",
        }
        session = _QueueSession([_QueueResult(row=row)])
        result = await omnichannel_api.approve_action(
            "action-id", user={"sub": "admin-1", "tenant_id": "tenant-1", "roles": ["platform_admin"]},
            s=session,
        )
        self.assertEqual(result["approval_status"], "approved")
        self.assertEqual(session.calls[0][1]["tenant"], "tenant-1")
        self.assertIn("status='queued' AND approval_status='pending'", session.calls[0][0])
        self.assertEqual(session.calls[0][1]["user_id"], "admin-1")
        self.assertEqual(session.commits, 1)



if __name__ == "__main__":
    unittest.main()
