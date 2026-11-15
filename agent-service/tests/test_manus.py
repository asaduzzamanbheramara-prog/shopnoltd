import os
import unittest
from unittest.mock import patch
from manus import manus_api_keys, manus_configured


class ManusCredentialTests(unittest.TestCase):
    def test_keys_are_read_in_stable_rotation_order(self):
        env = {
            "MANUS_API_KEY_1": "first",
            "MANUS_API_KEY_3": "third",
            "MANUS_API_KEY_5": "fifth",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(manus_api_keys(), ["first", "third", "fifth"])
            self.assertTrue(manus_configured())

    def test_missing_keys_disable_manus_tool(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(manus_api_keys(), [])
            self.assertFalse(manus_configured())

    def test_whitespace_keys_are_ignored(self):
        with patch.dict(os.environ, {"MANUS_API_KEY_1": "  "}, clear=True):
            self.assertEqual(manus_api_keys(), [])


if __name__ == "__main__":
    unittest.main()
