#!/usr/bin/env python3
"""Tests for the offline artifact-integrity checker."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "tools/software-os-diagnostics"))
import verify_artifact  # noqa: E402


class ArtifactVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "sample.iso"
        self.payload = b"sample artifact bytes\x00\xff"
        self.path.write_bytes(self.payload)

    def test_matching_sha256_passes(self):
        expected = hashlib.sha256(self.payload).hexdigest()
        self.assertTrue(verify_artifact.verify_file(self.path, "sha256", expected))

    def test_matching_sha512_passes(self):
        expected = hashlib.sha512(self.payload).hexdigest()
        self.assertTrue(verify_artifact.verify_file(self.path, "sha512", expected))

    def test_mismatch_fails(self):
        self.assertFalse(verify_artifact.verify_file(self.path, "sha256", "0" * 64))

    def test_malformed_digest_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_artifact.verify_file(self.path, "sha256", "not-a-digest")

    def test_unsupported_algorithm_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_artifact.verify_file(self.path, "md5", "0" * 32)

    def test_file_is_not_modified(self):
        before = self.path.read_bytes()
        verify_artifact.verify_file(self.path, "sha256", hashlib.sha256(before).hexdigest())
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
