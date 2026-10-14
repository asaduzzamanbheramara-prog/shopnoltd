"""Tests for the offline OpenPGP signature verifier; no key or image is modified."""
from __future__ import annotations

import subprocess
import shutil
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
    def test_rejects_signing_subkey_fingerprint_when_primary_key_is_not_expected(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout=self.status(), stderr="")
        valid, reason = verifier.verify_detached_signature(
            self.artifact, self.signature, self.keyring, self.signer, gpgv_path="gpgv"
        )
        self.assertFalse(valid)
        self.assertIn("does not match", reason)

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

@unittest.skipUnless(shutil.which("gpg") and shutil.which("gpgv"), "gpg and gpgv are required for real OpenPGP integration tests")
class RealOpenPGPIntegrationTests(unittest.TestCase):
    """Exercise gpg/gpgv with a throwaway key; never uses a real publisher key."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / "gnupg"
        self.home.mkdir(mode=0o700)
        self.env = dict(__import__("os").environ, GNUPGHOME=str(self.home))
        self.artifact = self.base / "fixture.iso"
        self.signature = self.base / "fixture.iso.sig"
        self.keyring = self.base / "fixture-trusted.gpg"
        self.artifact.write_bytes(b"safe test fixture; not an operating-system image")
        subprocess.run(
            [
                shutil.which("gpg"), "--batch", "--pinentry-mode", "loopback",
                "--passphrase", "", "--quick-generate-key",
                "Shopnoltd test fixture <fixture@example.invalid>", "rsa2048", "sign", "0",
            ],
            env=self.env, check=True, capture_output=True, text=True, timeout=60,
        )
        listing = subprocess.run(
            [shutil.which("gpg"), "--batch", "--with-colons", "--fingerprint", "--list-keys"],
            env=self.env, check=True, capture_output=True, text=True, timeout=15,
        )
        fingerprints = [
            line.split(":")[9].upper()
            for line in listing.stdout.splitlines()
            if line.startswith("fpr:") and len(line.split(":")) > 9
        ]
        self.fingerprint = fingerprints[0]
        exported = subprocess.run(
            [shutil.which("gpg"), "--batch", "--export", self.fingerprint],
            env=self.env, check=True, capture_output=True, timeout=15,
        )
        self.keyring.write_bytes(exported.stdout)
        subprocess.run(
            [
                shutil.which("gpg"), "--batch", "--yes", "--pinentry-mode", "loopback",
                "--passphrase", "", "--local-user", self.fingerprint,
                "--output", str(self.signature), "--detach-sign", str(self.artifact),
            ],
            env=self.env, check=True, capture_output=True, timeout=30,
        )

    def test_real_gpgv_signature_passes_for_expected_key(self):
        valid, reason = verifier.verify_detached_signature(
            self.artifact, self.signature, self.keyring, self.fingerprint
        )
        self.assertTrue(valid, reason)
        self.assertIn("expected fingerprint", reason)

    def test_real_gpgv_signature_fails_for_different_expected_key(self):
        wrong = ("0" if self.fingerprint[0] != "0" else "1") + self.fingerprint[1:]
        valid, reason = verifier.verify_detached_signature(
            self.artifact, self.signature, self.keyring, wrong
        )
        self.assertFalse(valid)
        self.assertIn("does not match", reason)

    def test_real_gpgv_detects_tampered_artifact(self):
        self.artifact.write_bytes(b"tampered fixture")
        valid, _ = verifier.verify_detached_signature(
            self.artifact, self.signature, self.keyring, self.fingerprint
        )
        self.assertFalse(valid)

