import os
import tempfile
import unittest
from unittest import mock

import httpx

os.environ.setdefault("LITELLM_MASTER_KEY", "ci-only-not-a-real-key")
os.environ.setdefault("WORKSPACE", tempfile.mkdtemp(prefix="shopno-agent-tests-"))

import main


class BrowserArgumentTests(unittest.TestCase):
    def test_accepts_public_http_url(self):
        self.assertEqual(
            main.validate_public_http_url("https://example.com/path"),
            "https://example.com/path",
        )

    def test_rejects_localhost_and_private_networks(self):
        for url in (
            "http://localhost/",
            "http://127.0.0.1/",
            "http://10.0.0.5/",
            "http://192.168.1.10/",
            "http://service.shopno-apps.svc/",
            "file:///etc/passwd",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                main.validate_public_http_url(url)

    def test_requires_selector_for_wait_for(self):
        with self.assertRaisesRegex(ValueError, "selector required"):
            main.clean_browser_args({"action": "wait_for"})

    def test_accepts_wait_for_selector(self):
        self.assertEqual(
            main.clean_browser_args({"action": "wait_for", "selector": "#ready"}),
            {"action": "wait_for", "selector": "#ready"},
        )

    def test_rejects_unknown_browser_action(self):
        with self.assertRaisesRegex(ValueError, "unknown browser action"):
            main.clean_browser_args({"action": "download_all_secrets"})


class ModelFailoverTests(unittest.TestCase):
    def setUp(self):
        self.previous = dict(main.model_cooldowns)
        main.model_cooldowns.clear()

    def tearDown(self):
        main.model_cooldowns.clear()
        main.model_cooldowns.update(self.previous)

    def test_auto_candidates_include_only_explicit_free_models(self):
        catalog = [
            {"model_key": "provider:free-a", "free_tier": True},
            {"model_key": "provider:paid-b", "free_tier": False},
            {"model_key": "provider:unknown-c"},
        ]
        self.assertEqual(main.eligible_free_models(catalog, set(), now=100), ["provider:free-a"])

    def test_auto_candidates_skip_failed_and_cooling_models(self):
        main.model_cooldowns["provider:cooling"] = 200
        catalog = [
            {"model_key": "provider:failed", "free_tier": True},
            {"model_key": "provider:cooling", "free_tier": True},
            {"model_key": "provider:ready", "free_tier": True},
        ]
        self.assertEqual(main.eligible_free_models(catalog, {"provider:failed"}, now=100), ["provider:ready"])

    def test_quota_and_provider_outages_are_retryable(self):
        request = httpx.Request("POST", "https://provider.example/v1/chat/completions")
        for status in (402, 408, 425, 429, 500, 502, 503, 504):
            response = httpx.Response(status, request=request)
            error = httpx.HTTPStatusError("provider error", request=request, response=response)
            with self.subTest(status=status):
                self.assertTrue(main.is_retryable_model_error(error))

    def test_bad_request_and_auth_errors_are_not_retryable(self):
        request = httpx.Request("POST", "https://provider.example/v1/chat/completions")
        for status in (400, 401, 403, 404, 422):
            response = httpx.Response(status, request=request)
            error = httpx.HTTPStatusError("client error", request=request, response=response)
            with self.subTest(status=status):
                self.assertFalse(main.is_retryable_model_error(error))

    def test_network_timeout_is_retryable(self):
        self.assertTrue(main.is_retryable_model_error(httpx.TimeoutException("timeout")))


class WorkspaceIsolationTests(unittest.TestCase):
    def setUp(self):
        self.previous_workspace = main.WORKSPACE
        self.temp = tempfile.TemporaryDirectory()
        main.WORKSPACE = self.temp.name

    def tearDown(self):
        main.WORKSPACE = self.previous_workspace
        self.temp.cleanup()

    def test_user_workspaces_are_separate(self):
        a = main.user_path("user-a", "notes.txt")
        b = main.user_path("user-b", "notes.txt")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith(os.path.join(self.temp.name, "user-a") + os.sep))
        self.assertTrue(b.startswith(os.path.join(self.temp.name, "user-b") + os.sep))

    def test_rejects_parent_traversal(self):
        with self.assertRaisesRegex(ValueError, "path escapes workspace"):
            main.user_path("user-a", "../../outside.txt")

    def test_rejects_symlink_escape(self):
        user_root = main.user_path("user-a", ".")
        outside = os.path.join(self.temp.name, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(user_root, "escape"))
        with self.assertRaisesRegex(ValueError, "path escapes workspace"):
            main.user_path("user-a", "escape/secret.txt")


class WebSocketAuthenticationDisconnectTests(unittest.IsolatedAsyncioTestCase):
    async def test_disconnect_before_first_auth_message_is_handled_cleanly(self):
        class DisconnectedSocket:
            headers = {"origin": main.UI_ORIGINS[0]}

            def __init__(self):
                self.accepted = False
                self.close_called = False

            async def accept(self):
                self.accepted = True

            async def receive_json(self):
                raise main.WebSocketDisconnect(code=1005)

            async def close(self, code):
                self.close_called = True
                raise AssertionError("disconnected socket must not receive a close frame")

        ws = DisconnectedSocket()
        claims = await main.authenticate(ws, "ui")

        self.assertTrue(ws.accepted)
        self.assertIsNone(claims)
        self.assertFalse(ws.close_called)


    async def test_disconnect_while_sending_auth_confirmation_returns_none(self):
        class AuthenticatedSocket:
            headers = {"origin": main.UI_ORIGINS[0]}

            async def accept(self):
                pass

            async def receive_json(self):
                return {"type": "auth", "token": "test-token"}

            async def send_json(self, message):
                raise main.WebSocketDisconnect(code=1006)

        ws = AuthenticatedSocket()
        with mock.patch.object(
            main, "verify_token", new=mock.AsyncMock(return_value={"sub": "user-a"})
        ):
            claims = await main.authenticate(ws, "ui")

        self.assertIsNone(claims)




class BrowserApprovalModeTests(unittest.IsolatedAsyncioTestCase):
    async def _check_policy(self, mode, action, approval_expected):
        args = {"action": action}
        if action == "open":
            args["url"] = "https://example.com/"
        elif action in {"click", "type", "press", "select", "check", "uncheck", "submit", "upload", "wait_for"}:
            args["selector"] = "#target"
        if action == "type":
            args["text"] = "hello"
        if action == "press":
            args["key"] = "Enter"
        if action == "select":
            args["value"] = "option-a"
        if action == "upload":
            args["path"] = "file.txt"

        ui = mock.AsyncMock()
        with (
            mock.patch.object(main, "ask_approval", new=mock.AsyncMock(return_value=True)) as approval,
            mock.patch.object(main, "browser_action", new=mock.AsyncMock(return_value='{"ok": true}')) as execute,
        ):
            result = await main.call_tool({"sub": "user-a"}, ui, "browser_action", args, mode)

        self.assertEqual(result, '{"ok": true}')
        self.assertEqual(approval.await_count, 1 if approval_expected else 0)
        execute.assert_awaited_once()

    async def test_auto_runs_routine_actions_without_approval(self):
        for action in ("open", "get_text", "click", "type", "scroll", "select", "check", "uncheck"):
            with self.subTest(action=action):
                await self._check_policy("auto", action, False)

    async def test_auto_still_requires_approval_for_sensitive_actions(self):
        for action in ("press", "submit", "upload"):
            with self.subTest(action=action):
                await self._check_policy("auto", action, True)

    async def test_hybrid_approves_mutations_but_allows_inspection(self):
        for action, expected in (("open", False), ("get_text", False), ("screenshot", False),
                                 ("wait_for", False), ("click", True), ("type", True),
                                 ("scroll", False), ("submit", True), ("upload", True)):
            with self.subTest(action=action):
                await self._check_policy("hybrid", action, expected)

    async def test_manual_approves_state_changing_browser_actions(self):
        for action, expected in (("open", True), ("get_text", False), ("screenshot", False),
                                 ("wait_for", False), ("click", True), ("type", True),
                                 ("scroll", True), ("press", True), ("submit", True),
                                 ("upload", True)):
            with self.subTest(action=action):
                await self._check_policy("manual", action, expected)

    async def test_denied_action_never_reaches_browser(self):
        ui = mock.AsyncMock()
        with (
            mock.patch.object(main, "ask_approval", new=mock.AsyncMock(return_value=False)),
            mock.patch.object(main, "browser_action", new=mock.AsyncMock()) as execute,
        ):
            result = await main.call_tool(
                {"sub": "user-a"}, ui, "browser_action",
                {"action": "click", "selector": "#delete"}, "hybrid",
            )
        self.assertEqual(result, "user denied this action")
        execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
