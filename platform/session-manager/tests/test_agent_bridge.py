import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./session-manager-agent-bridge-tests.db")

from fastapi import HTTPException

from app.routers import agent_bridge


class FakeQuery:
    def __init__(self, value):
        self.value = value

    def filter(self, *_args):
        return self

    def first(self):
        return self.value


class FakeDB:
    def __init__(self, profile):
        self.profile = profile

    def query(self, *_args):
        return FakeQuery(self.profile)


class AgentBridgeAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cross_user_profile_is_hidden(self):
        db = FakeDB(None)
        payload = agent_bridge.AgentBrowserAction(action="get_text")
        with self.assertRaises(HTTPException) as caught:
            await agent_bridge.agent_browser_action(
                "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002", payload, {"sub": "user-b"}, db
            )
        self.assertEqual(caught.exception.status_code, 404)

    async def test_closed_session_is_rejected(self):
        profile = SimpleNamespace(owner="user-a")
        db = FakeDB(profile)
        payload = agent_bridge.AgentBrowserAction(action="get_text")
        with patch.object(agent_bridge.pool, "_contexts", {}):
            with self.assertRaises(HTTPException) as caught:
                await agent_bridge.agent_browser_action(
                    "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002", payload, {"sub": "user-a"}, db
                )
        self.assertEqual(caught.exception.status_code, 409)

    async def test_unknown_tab_is_rejected(self):
        profile = SimpleNamespace(owner="user-a")
        db = FakeDB(profile)
        payload = agent_bridge.AgentBrowserAction(action="get_text")
        with (
            patch.object(agent_bridge.pool, "_contexts", {"00000000-0000-4000-8000-000000000001": object()}),
            patch.object(agent_bridge.pool, "_get_tab", return_value=None),
        ):
            with self.assertRaises(HTTPException) as caught:
                await agent_bridge.agent_browser_action(
                    "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000003", payload, {"sub": "user-a"}, db
                )
        self.assertEqual(caught.exception.status_code, 404)

    async def test_private_navigation_is_blocked(self):
        profile = SimpleNamespace(owner="user-a")
        db = FakeDB(profile)
        payload = agent_bridge.AgentBrowserAction(action="open", url="http://127.0.0.1/")
        fake_page = SimpleNamespace()
        with (
            patch.object(agent_bridge.pool, "_contexts", {"00000000-0000-4000-8000-000000000001": object()}),
            patch.object(agent_bridge.pool, "_get_tab", return_value=fake_page),
        ):
            with self.assertRaises(HTTPException) as caught:
                await agent_bridge.agent_browser_action(
                    "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002", payload, {"sub": "user-a"}, db
                )
        self.assertEqual(caught.exception.status_code, 400)

    async def test_screenshot_is_returned_from_the_selected_tab(self):
        profile = SimpleNamespace(owner="user-a")
        db = FakeDB(profile)

        class FakePage:
            url = "https://example.com/"

            async def screenshot(self, **_kwargs):
                return b"jpeg-bytes"

        with (
            patch.object(agent_bridge.pool, "_contexts", {"00000000-0000-4000-8000-000000000001": object()}),
            patch.object(agent_bridge.pool, "_get_tab", return_value=FakePage()),
        ):
            result = await agent_bridge.agent_browser_action(
                "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002", agent_bridge.AgentBrowserAction(action="screenshot"),
                {"sub": "user-a"}, db
            )
        self.assertTrue(result["image"].startswith("data:image/jpeg;base64,"))

    async def test_upload_payload_is_size_limited_and_sanitized(self):
        profile = SimpleNamespace(owner="user-a")
        db = FakeDB(profile)

        class FakeLocator:
            first = None

            async def set_input_files(self, file_payload, **_kwargs):
                self.file_payload = file_payload

        locator = FakeLocator()
        locator.first = locator

        class FakePage:
            def locator(self, _selector):
                return locator

        with (
            patch.object(agent_bridge.pool, "_contexts", {"00000000-0000-4000-8000-000000000001": object()}),
            patch.object(agent_bridge.pool, "_get_tab", return_value=FakePage()),
        ):
            result = await agent_bridge.agent_browser_action(
                "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002",
                agent_bridge.AgentBrowserAction(
                    action="upload", selector="input[type=file]", file_name="../my report.txt",
                    content_base64="c2FmZSBmaWxl"
                ),
                {"sub": "user-a"}, db
            )
        self.assertTrue(result["uploaded"])
        self.assertEqual(result["filename"], "_my report.txt")
        self.assertEqual(locator.file_payload["buffer"], b"safe file")

    async def test_keyboard_shortcuts_are_limited(self):
        profile = SimpleNamespace(owner="user-a")
        db = FakeDB(profile)
        payload = agent_bridge.AgentBrowserAction(
            action="press", selector="body", key="Alt+F4"
        )
        fake_page = SimpleNamespace()
        with (
            patch.object(agent_bridge.pool, "_contexts", {"00000000-0000-4000-8000-000000000001": object()}),
            patch.object(agent_bridge.pool, "_get_tab", return_value=fake_page),
        ):
            with self.assertRaises(HTTPException) as caught:
                await agent_bridge.agent_browser_action(
                    "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002", payload, {"sub": "user-a"}, db
                )
        self.assertEqual(caught.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
