import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent


class ExecutorEnrollmentTests(unittest.TestCase):
    def test_complete_enrollment_persists_agent_credentials_without_token(self):
        original = {"gateway_url": "https://remote.example", "device_id": "device-1", "enrollment_token": "one-time"}
        response = {"ok": True, "agent_id": "agent-1", "secret": "base64-secret"}
        with patch.object(agent, "save_config_secure") as save:
            result = agent.complete_enrollment(original, response)

        self.assertEqual(result["agent_id"], "agent-1")
        self.assertEqual(result["secret"], "base64-secret")
        self.assertNotIn("enrollment_token", result)
        save.assert_called_once_with(result)
        self.assertIn("enrollment_token", original)  # caller's input is not mutated

    def test_complete_enrollment_rejects_incomplete_response(self):
        with self.assertRaisesRegex(RuntimeError, "did not include agent_id and secret"):
            agent.complete_enrollment({"enrollment_token": "one-time"}, {"ok": True})

    def test_secure_config_write_is_atomic_and_private_on_posix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "executor.json"
            with patch.object(agent, "CONFIG_PATH", path), patch.object(agent.platform, "system", return_value="Linux"):
                agent.save_config_secure({"device_id": "device-1", "secret": "do-not-print"})
            self.assertTrue(path.exists())
            self.assertFalse(path.with_name(path.name + ".tmp").exists())
            self.assertEqual(json.loads(path.read_text())["secret"], "do-not-print")
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(path.parent).st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
