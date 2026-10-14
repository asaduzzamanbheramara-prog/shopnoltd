"""Schema and policy regression tests for recovery image metadata."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "catalogue/schema/recovery-image-manifest.schema.json").read_text(encoding="utf-8"))
TEMPLATE = ROOT / "catalogue/recovery-images/linux-recovery-image-template.json"
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


class RecoveryImageManifestTests(unittest.TestCase):
    def test_template_is_valid_but_not_approved(self):
        manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(list(VALIDATOR.iter_errors(manifest)), [])
        self.assertEqual(manifest["validation_status"], "draft")
        self.assertEqual(manifest["verification"]["status"], "not-verified")
        self.assertEqual(manifest["boot_test"]["status"], "not-tested")

    def test_approved_manifest_requires_verification_and_boot_test(self):
        manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        manifest["validation_status"] = "approved-for-listing"
        errors = list(VALIDATOR.iter_errors(manifest))
        self.assertTrue(errors)

    def test_untrusted_http_source_is_rejected(self):
        manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        manifest["official_source_url"] = "http://example.com/image.iso"
        self.assertTrue(list(VALIDATOR.iter_errors(manifest)))

    def test_cli_accepts_template(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate-recovery-image-manifest.py"), str(TEMPLATE)],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_rejects_invalid_manifest(self):
        manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        manifest["minimum_usb_capacity_gib"] = 0
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/validate-recovery-image-manifest.py"), str(path)],
                check=False, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("minimum_usb_capacity_gib", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
