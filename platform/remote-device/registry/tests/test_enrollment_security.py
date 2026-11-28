import importlib.util
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from fastapi import HTTPException
from starlette.requests import Request


REPO = Path(__file__).resolve().parents[4]
CONFIGMAP = REPO / "k8s/services/remote-device/registry-configmap-v4.yaml"


class RegistryEnrollmentSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="shopno-registry-tests-")
        os.environ["DATA_DIR"] = cls.temp_dir.name
        os.environ["REGISTRY_CONTROL_TOKEN"] = "ci-only-registry-control-token"
        config = yaml.safe_load(CONFIGMAP.read_text(encoding="utf-8"))
        source = config["data"]["app.py"]
        cls.module = type("RegistryModule", (), {})()
        exec(compile(source, str(CONFIGMAP) + ":app.py", "exec"), cls.module.__dict__)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()
        os.environ.pop("DATA_DIR", None)
        os.environ.pop("REGISTRY_CONTROL_TOKEN", None)

    def setUp(self):
        self.module = self.__class__.module
        self.module.save_devices([])
        self.module.save_jobs([])
        self.module.save_nonces({})

    def control_request(self):
        return Request({
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [(b"x-shopnoltd-control-token", b"ci-only-registry-control-token")],
            "server": ("test", 80),
            "client": ("test", 1234),
        })

    def new_device(self):
        return self.module.create_device(
            self.module.DeviceCreate(name="CI test device", platform="windows", owner_id="ci-user")
        )

    def test_new_enrollment_token_is_hashed_and_expires(self):
        created = self.new_device()
        stored = self.module.load_devices()[0]
        self.assertNotIn("enrollment_token", stored)
        self.assertEqual(
            stored["enrollment_token_hash"],
            self.module.hashlib.sha256(created.enrollment_token.encode()).hexdigest(),
        )
        expiry = datetime.fromisoformat(stored["enrollment_token_expires_at"])
        self.assertGreater(expiry, datetime.now(timezone.utc))
        self.assertLessEqual(expiry, datetime.now(timezone.utc) + timedelta(minutes=21))

    def test_successful_enrollment_consumes_token_and_replay_is_rejected(self):
        created = self.new_device()
        request = self.module.ExecutorEnroll(
            enrollment_token=created.enrollment_token,
            hostname="ci-host",
            platform="windows",
        )
        result = self.module.executor_enroll(created.id, request)
        self.assertTrue(result["secret"])
        stored = self.module.load_devices()[0]
        self.assertIsNone(stored.get("enrollment_token_hash"))
        self.assertIsNone(stored.get("enrollment_token_expires_at"))
        with self.assertRaises(HTTPException) as caught:
            self.module.executor_enroll(created.id, request)
        self.assertEqual(caught.exception.status_code, 409)

    def test_expired_token_is_rejected(self):
        created = self.new_device()
        stored = self.module.load_devices()
        stored[0]["enrollment_token_expires_at"] = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        ).isoformat()
        self.module.save_devices(stored)
        request = self.module.ExecutorEnroll(
            enrollment_token=created.enrollment_token,
            hostname="ci-host",
            platform="windows",
        )
        with self.assertRaises(HTTPException) as caught:
            self.module.executor_enroll(created.id, request)
        self.assertEqual(caught.exception.status_code, 410)

    def test_legacy_plaintext_token_older_than_twenty_minutes_is_rejected(self):
        created = self.new_device()
        stored = self.module.load_devices()
        stored[0]["enrollment_token"] = created.enrollment_token
        stored[0].pop("enrollment_token_hash", None)
        stored[0].pop("enrollment_token_expires_at", None)
        stored[0]["created_at"] = (
            datetime.now(timezone.utc) - timedelta(minutes=21)
        ).isoformat()
        self.module.save_devices(stored)
        request = self.module.ExecutorEnroll(
            enrollment_token=created.enrollment_token,
            hostname="ci-host",
            platform="windows",
        )
        with self.assertRaises(HTTPException) as caught:
            self.module.executor_enroll(created.id, request)
        self.assertEqual(caught.exception.status_code, 410)

    def test_regenerate_replaces_legacy_token_with_hashed_expiring_token(self):
        created = self.new_device()
        stored = self.module.load_devices()
        stored[0]["enrollment_token"] = "old-legacy-token-value"
        stored[0].pop("enrollment_token_hash", None)
        stored[0].pop("enrollment_token_expires_at", None)
        self.module.save_devices(stored)
        result = self.module.regenerate_enrollment_token(created.id, self.control_request())
        stored = self.module.load_devices()[0]
        self.assertNotIn("enrollment_token", stored)
        self.assertEqual(
            stored["enrollment_token_hash"],
            self.module.hashlib.sha256(result["enrollment_token"].encode()).hexdigest(),
        )
        self.assertEqual(result["expires_in_seconds"], 1200)

    def test_stale_executor_is_reported_offline(self):
        created = self.new_device()
        self.module.executor_enroll(
            created.id,
            self.module.ExecutorEnroll(
                enrollment_token=created.enrollment_token,
                hostname="ci-host",
                platform="windows",
            ),
        )
        stored = self.module.load_devices()
        stored[0]["executor_last_seen"] = (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        ).isoformat()
        self.module.save_devices(stored)
        self.assertEqual(self.module.public_device(stored[0]).status, "offline")


    def test_pairing_session_secret_is_hashed_and_single_use(self):
        created = self.new_device()
        result = self.module.create_pairing_session(
            created.id,
            self.module.PairingCreate(platform="windows", created_by="ci-user"),
            self.control_request(),
        )
        stored = self.module.load_devices()[0]
        pairing = stored["pairing_session"]
        self.assertNotIn("pairing_secret", pairing)
        self.assertEqual(pairing["secret_hash"], self.module.hashlib.sha256(result["pairing_secret"].encode()).hexdigest())
        consumed = self.module.consume_pairing_session(
            self.module.PairingConsume(device_id=created.id, pairing_secret=result["pairing_secret"], hostname="ci-host", platform="windows")
        )
        self.assertTrue(consumed["enrollment_token"])
        self.assertEqual(self.module.load_devices()[0]["pairing_session"]["status"], "consumed")
        with self.assertRaises(HTTPException) as caught:
            self.module.consume_pairing_session(
                self.module.PairingConsume(pairing_secret=result["pairing_secret"], hostname="ci-host", platform="windows")
            )
        self.assertEqual(caught.exception.status_code, 401)

    def test_pairing_rejects_platform_mismatch(self):
        created = self.new_device()
        result = self.module.create_pairing_session(
            created.id,
            self.module.PairingCreate(platform="windows", created_by="ci-user"),
            self.control_request(),
        )
        with self.assertRaises(HTTPException) as caught:
            self.module.consume_pairing_session(
                self.module.PairingConsume(device_id=created.id, pairing_secret=result["pairing_secret"], hostname="ci-host", platform="android")
            )
        self.assertEqual(caught.exception.status_code, 403)

    def test_pairing_expiry_and_revocation_are_enforced(self):
        created = self.new_device()
        result = self.module.create_pairing_session(
            created.id,
            self.module.PairingCreate(platform="windows", created_by="ci-user"),
            self.control_request(),
        )
        stored = self.module.load_devices()
        stored[0]["pairing_session"]["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self.module.save_devices(stored)
        with self.assertRaises(HTTPException) as caught:
            self.module.consume_pairing_session(
                self.module.PairingConsume(pairing_secret=result["pairing_secret"], hostname="ci-host", platform="windows")
            )
        self.assertEqual(caught.exception.status_code, 410)

        created2 = self.new_device()
        result2 = self.module.create_pairing_session(
            created2.id,
            self.module.PairingCreate(platform="windows", created_by="ci-user"),
            self.control_request(),
        )
        revoked = self.module.revoke_pairing_session(created2.id, self.control_request())
        self.assertEqual(revoked["status"], "revoked")
        with self.assertRaises(HTTPException) as caught2:
            self.module.consume_pairing_session(
                self.module.PairingConsume(device_id=created2.id, pairing_secret=result2["pairing_secret"], hostname="ci-host", platform="windows")
            )
        self.assertEqual(caught2.exception.status_code, 401)

    def test_delete_requires_authenticated_gateway(self):
        created = self.new_device()
        unauthenticated = Request({
            "type": "http", "http_version": "1.1", "method": "DELETE",
            "scheme": "http", "path": "/", "raw_path": b"/",
            "query_string": b"", "headers": [],
            "server": ("test", 80), "client": ("test", 1234),
        })
        with self.assertRaises(HTTPException) as caught:
            self.module.delete_device(created.id, unauthenticated)
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(len(self.module.load_devices()), 1)

    def test_authenticated_gateway_can_delete_device(self):
        created = self.new_device()
        result = self.module.delete_device(created.id, self.control_request())
        self.assertTrue(result["ok"])
        self.assertEqual(self.module.load_devices(), [])


if __name__ == "__main__":
    unittest.main()
