import os
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
