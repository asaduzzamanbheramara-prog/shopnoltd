"""Tests for the offline OpenPGP signature verifier; no key or image is modified."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "tools/software-os-diagnostics"))
import verify_detached_signature as verifier  # noqa: E402


class DetachedSignatureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.artifact = base / "image.iso"
        self.signature = base / "image.iso.sig"
        self.keyring = base / "trusted.gpg"
        for path in (self.artifact, self.signature, self.keyring):
            path.write_bytes(b"fixture")
        self.signer = "A" * 40
        self.primary = "B" * 40

    def status(self, signing=None, primary=None):
        signing = signing or self.signer
        primary = primary or self.primary
        return (
            "[GNUPG:] NEWSIG\n"
            f"[GNUPG:] VALIDSIG {signing} 20261014 1792000000 0 4 0 1 8 00 {primary}\n"
        )

    @patch("verify_detached_signature.subprocess.run")
    def test_accepts_valid_signature_from_expected_primary_key(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout=self.status(), stderr="")
        valid, reason = verifier.verify_detached_signature(
            self.artifact, self.signature, self.keyring, self.primary, gpgv_path="gpgv"
        )
        self.assertTrue(valid)
        self.assertIn("expected fingerprint", reason)
        self.assertEqual(run.call_args.args[0][-2:], [str(self.signature), str(self.artifact)])

    @patch("verify_detached_signature.subprocess.run")
    def test_rejects_valid_signature_from_wrong_key(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout=self.status(), stderr="")
        valid, reason = verifier.verify_detached_signature(
            self.artifact, self.signature, self.keyring, "C" * 40, gpgv_path="gpgv"
        )
        self.assertFalse(valid)
        self.assertIn("does not match", reason)

    @patch("verify_detached_signature.subprocess.run")
    def test_rejects_gpgv_failure_even_if_status_is_present(self, run):
        run.return_value = SimpleNamespace(returncode=1, stdout=self.status(), stderr="bad signature")
        valid, _ = verifier.verify_detached_signature(
            self.artifact, self.signature, self.keyring, self.signer, gpgv_path="gpgv"
        )
        self.assertFalse(valid)

    def test_rejects_malformed_expected_fingerprint_before_running_gpgv(self):
        with patch("verify_detached_signature.subprocess.run") as run:
            with self.assertRaises(ValueError):
                verifier.verify_detached_signature(
                    self.artifact, self.signature, self.keyring, "not-a-fingerprint", gpgv_path="gpgv"
                )
            run.assert_not_called()

    def test_missing_artifact_is_rejected(self):
        with self.assertRaises(ValueError):
            verifier.verify_detached_signature(
                self.artifact.with_name("missing.iso"), self.signature, self.keyring,
                self.signer, gpgv_path="gpgv"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
