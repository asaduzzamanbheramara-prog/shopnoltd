#!/usr/bin/env python3
"""Safety tests for the read-only diagnostics starter."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/software-os-diagnostics"))
import diagnose  # noqa: E402


class ReadOnlyDiagnosticsTests(unittest.TestCase):
    def test_report_has_only_expected_safe_fields(self):
        report = diagnose.collect_report()
        self.assertEqual(
            set(report),
            {
                "tool", "tool_version", "os_family", "os_release",
                "architecture", "python_version", "home_volume_total_bytes",
                "home_volume_free_bytes", "mode", "actions_performed",
            },
        )
        self.assertEqual(report["mode"], "read-only-offline")
        self.assertEqual(report["actions_performed"], [])
        self.assertNotIn("home_path", report)
        self.assertNotIn("username", report)
        self.assertNotIn("serial_number", report)

    def test_report_does_not_make_network_requests(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network access forbidden")):
            report = diagnose.collect_report()
        self.assertEqual(report["mode"], "read-only-offline")

    def test_report_is_json_serializable(self):
        json.dumps(diagnose.collect_report())


if __name__ == "__main__":
    unittest.main(verbosity=2)
