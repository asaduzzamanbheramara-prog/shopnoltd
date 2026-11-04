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


    def test_tutorial_schema_supports_provenance_and_review_metadata(self):
        tutorial = SCHEMA["properties"]["tutorials"]["items"]["properties"]
        self.assertEqual(set(tutorial["source_kind"]["enum"]), {
            "official-vendor", "shopnoltd-owned", "community-reference"
        })
        self.assertEqual(set(tutorial["privacy_review"]["enum"]), {
            "not-applicable", "pending", "passed"
        })
        self.assertEqual(tutorial["last_reviewed"]["format"], "date")
        self.assertEqual(tutorial["captions_available"]["type"], "boolean")
        page = (ROOT / "frontend/software-os-center.html").read_text(encoding="utf-8")
        self.assertIn("tutorial.source_kind", page)
        self.assertIn("tutorial.privacy_review", page)
        self.assertIn("tutorial.last_reviewed", page)


    def test_catalogue_page_exposes_device_and_package_metadata(self):
        page = (ROOT / "frontend/software-os-center.html").read_text(encoding="utf-8")
        self.assertIn("entry.device_types", page)
        self.assertIn("entry.package_formats", page)
        self.assertIn("entry.package_formats||[]", page)


    def test_schema_exposes_broad_software_categories(self):
        categories = set(SCHEMA["properties"]["categories"]["items"]["enum"])
        self.assertTrue({
            "browser", "office-productivity", "developer-tools", "programming-runtimes",
            "security-privacy", "drivers-firmware", "media-creative", "education-science",
            "communication", "utilities", "server-self-hosted", "database-storage",
            "backup-recovery", "accessibility", "gaming", "system-administration",
            "design-engineering", "other"
        } <= categories)

    def test_catalogue_page_searches_and_displays_categories(self):
        page = (ROOT / "frontend/software-os-center.html").read_text(encoding="utf-8")
        self.assertIn("entry.categories||[]", page)
        self.assertIn("Categories:", page)

if __name__ == "__main__":
    unittest.main(verbosity=2)
