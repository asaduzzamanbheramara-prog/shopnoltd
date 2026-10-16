#!/usr/bin/env python3
"""Coverage regression tests for multiple device and package families."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "catalogue/schema/software-entry.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

class DevicePackageCoverageTests(unittest.TestCase):
    def test_schema_accepts_android_apk_entry(self):
        entry = json.loads((ROOT / "catalogue/entries/fdroid-android-client.json").read_text(encoding="utf-8"))
        self.assertEqual(list(VALIDATOR.iter_errors(entry)), [])
        self.assertIn("android", entry["platforms"])
        self.assertIn("apk", entry["package_formats"])
        self.assertIn("phone", entry["device_types"])

    def test_schema_exposes_broad_platform_families(self):
        platforms = set(SCHEMA["properties"]["platforms"]["items"]["enum"])
        self.assertTrue({"windows", "linux", "macos", "android", "ios", "ipados", "chromeos", "tvos", "watchos", "harmonyos", "kaios", "bsd", "web", "firmware", "other"} <= platforms)

    def test_schema_exposes_common_package_formats_including_apk(self):
        formats = set(SCHEMA["properties"]["package_formats"]["items"]["enum"])
        self.assertTrue({"exe", "msi", "dmg", "pkg", "deb", "rpm", "appimage", "flatpak", "snap", "apk", "apks", "xapk", "aab", "ipa", "iso", "img", "container", "firmware", "web-app"} <= formats)

    def test_catalogue_page_exposes_device_and_package_metadata(self):
        page = (ROOT / "frontend/software-os-center.html").read_text(encoding="utf-8")
        self.assertIn("entry.device_types", page)
        self.assertIn("entry.package_formats", page)
        self.assertIn("entry.package_formats||[]", page)

if __name__ == "__main__":
    unittest.main(verbosity=2)
