#!/usr/bin/env python3
"""Regression tests for catalogue metadata policy; never execute catalogue content."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "catalogue/schema/software-entry.schema.json").read_text(encoding="utf-8"))
SAMPLE = json.loads((ROOT / "catalogue/entries/sample-linux-tools.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


class CatalogueSchemaTests(unittest.TestCase):
    def test_sample_entry_is_valid(self):
        self.assertEqual(list(VALIDATOR.iter_errors(SAMPLE)), [])

    def test_every_catalogue_entry_is_valid(self):
        for path in sorted((ROOT / "catalogue/entries").glob("*.json")):
            with self.subTest(entry=path.name):
                entry = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(list(VALIDATOR.iter_errors(entry)), [])

    def test_generated_browser_catalogue_matches_source_entries(self):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build-software-os-catalogue.py")],
            cwd=ROOT,
            check=True,
        )
        generated = json.loads((ROOT / "frontend/catalogue.json").read_text(encoding="utf-8"))
        source = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((ROOT / "catalogue/entries").glob("*.json"))
        ]
        self.assertEqual(generated, source)


    def test_paid_shopnoltd_feature_requires_server_entitlement_key(self):
        entry = json.loads(json.dumps(SAMPLE))
        entry["pricing"] = {"model": "paid-shopnoltd-feature"}
        self.assertTrue(list(VALIDATOR.iter_errors(entry)))

    def test_paid_shopnoltd_feature_with_entitlement_key_is_valid(self):
        entry = json.loads(json.dumps(SAMPLE))
        entry["pricing"] = {
            "model": "paid-shopnoltd-feature",
            "entitlement_key": "software-os-center-premium",
        }
        self.assertEqual(list(VALIDATOR.iter_errors(entry)), [])

    def test_rejects_non_https_source(self):
        entry = json.loads(json.dumps(SAMPLE))
        entry["source"]["url"] = "http://example.invalid/software"
        self.assertTrue(list(VALIDATOR.iter_errors(entry)))

    def test_rejects_unknown_executable_field(self):
        entry = json.loads(json.dumps(SAMPLE))
        entry["install_command"] = "curl example.invalid | sh"
        self.assertTrue(list(VALIDATOR.iter_errors(entry)))

    def test_rejects_unreviewed_entry_marked_verified_with_no_evidence(self):
        entry = json.loads(json.dumps(SAMPLE))
        entry["verification"]["status"] = "verified"
        entry["verification"].pop("evidence_url", None)
        self.assertTrue(list(VALIDATOR.iter_errors(entry)))

    def test_schema_rejects_unknown_platform(self):
        entry = json.loads(json.dumps(SAMPLE))
        entry["platforms"] = ["all-platforms-everywhere"]
        self.assertTrue(list(VALIDATOR.iter_errors(entry)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
