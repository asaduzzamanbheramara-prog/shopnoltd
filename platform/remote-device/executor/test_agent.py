import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent


class ExecutorEnrollmentTests(unittest.TestCase):
    def test_termux_environment_is_reported_as_android(self):
        with patch.dict(os.environ, {"ANDROID_ROOT": "/system"}, clear=False):
            self.assertEqual(agent.reported_platform(), "Android")

    def test_non_android_host_uses_native_platform_name(self):
        with patch.dict(os.environ, {"ANDROID_ROOT": "", "ANDROID_DATA": ""}, clear=False), patch.object(agent.Path, "exists", return_value=False):
            self.assertEqual(agent.reported_platform(), agent.platform.system())

    def test_android_memory_status_reads_available_memory(self):
        meminfo = "MemTotal: 1024 kB\nMemAvailable: 256 kB\n"
        with patch.object(agent.platform, "system", return_value="Linux"), patch.object(agent.Path, "exists", return_value=True), patch.object(agent.Path, "read_text", return_value=meminfo):
            result = agent.operation_memory_status()
        self.assertEqual(result["total_bytes"], 1024 * 1024)
        self.assertEqual(result["available_bytes"], 256 * 1024)
        self.assertEqual(result["used_bytes"], 768 * 1024)

    def test_android_disk_status_uses_home_filesystem(self):
        from types import SimpleNamespace
        with patch.object(agent.platform, "system", return_value="Linux"), patch.object(agent.Path, "home", return_value=Path("/data/data/com.termux/files/home")), patch.object(agent.shutil, "disk_usage", return_value=SimpleNamespace(total=1000, used=600, free=400)):
            result = agent.operation_disk_status()
        self.assertEqual(result["total_bytes"], 1000)
        self.assertEqual(result["free_bytes"], 400)

    def test_termux_installer_expands_arguments_and_pins_agent_hash(self):
        installer = Path(__file__).with_name("install-termux.sh").read_text(encoding="utf-8")
        windows_installer = Path(__file__).with_name("install-windows.ps1").read_text(encoding="utf-8")
        agent_source = Path(__file__).with_name("agent.py").read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
        expected_hash = agent.hashlib.sha256(agent_source).hexdigest()
        self.assertIn('DEVICE_ID="${1:-}"', installer)
        self.assertIn('GATEWAY_URL="${2:-https://devices.shopnoltd.dpdns.org}"', installer)
        self.assertIn('if [[ -z "${PREFIX:-}"', installer)
        self.assertNotIn(r"\${1:-}", installer)
        self.assertNotIn(r"\${2:-", installer)
        self.assertNotIn(r"\${PREFIX:-}", installer)
        self.assertIn(expected_hash, installer)
        self.assertIn(expected_hash, windows_installer)

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


    def test_spent_enrollment_token_exits_without_retry_loop(self):
        import io
        from urllib.error import HTTPError
        config = {"gateway_url": "https://remote.example", "device_id": "device-1", "enrollment_token": "one-time"}
        error = HTTPError("https://remote.example", 409, "Conflict", {}, io.BytesIO(b'{"detail":"enrollment token unavailable"}'))
        with patch.object(agent, "urlopen", side_effect=error):
            with self.assertRaises(agent.EnrollmentRejected):
                agent.enroll(config)
        with patch.object(agent, "load_config", return_value=config), patch.object(agent, "prepare_config_storage"), patch.object(agent, "enroll", side_effect=agent.EnrollmentRejected("HTTP 409")):
            with self.assertRaises(SystemExit) as caught:
                agent.main()
        self.assertEqual(caught.exception.code, agent.EXIT_ENROLLMENT_REJECTED)

    def test_server_errors_during_enrollment_stay_retryable(self):
        import io
        from urllib.error import HTTPError
        config = {"gateway_url": "https://remote.example", "device_id": "device-1", "enrollment_token": "one-time"}
        error = HTTPError("https://remote.example", 502, "Bad Gateway", {}, io.BytesIO(b"bad gateway"))
        with patch.object(agent, "urlopen", side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                agent.enroll(config)
        self.assertNotIsInstance(caught.exception, agent.EnrollmentRejected)

    def test_wsl_unit_does_not_restart_after_rejected_enrollment(self):
        unit = Path(__file__).with_name("install-wsl.sh").read_text(encoding="utf-8")
        self.assertIn("RestartPreventExitStatus=%d" % agent.EXIT_ENROLLMENT_REJECTED, unit)



if __name__ == "__main__":
    unittest.main()
