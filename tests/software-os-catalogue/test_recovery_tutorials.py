#!/usr/bin/env python3
"""Regression tests for safe, clearly scoped recovery tutorial references."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "catalogue/schema/software-entry.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


class RecoveryTutorialTests(unittest.TestCase):
    def load_entry(self, name: str) -> dict:
        return json.loads((ROOT / "catalogue/entries" / name).read_text(encoding="utf-8"))

    def test_hp_recovery_video_is_official_and_not_claimed_model_tested(self):
        entry = self.load_entry("hp-14s-cf2xxx-windows-recovery.json")
        self.assertEqual(list(VALIDATOR.iter_errors(entry)), [])
        videos = [item for item in entry.get("tutorials", []) if item["type"] == "video"]
        self.assertEqual(len(videos), 2)
        self.assertTrue(all(urlparse(item["url"]).hostname == "www.youtube.com" for item in videos))
        self.assertTrue(all(item["publisher"] == "HP Support" for item in videos))
        self.assertTrue(all(item["status"] == "official-reference" for item in videos))
        self.assertTrue(all("not proof" in item["scope"].lower() or "does not validate" in item["scope"].lower() for item in videos))

    def test_realme_c35_uses_official_written_guides_without_fake_video_claim(self):
        entry = self.load_entry("realme-c35-rmx3511-recovery.json")
        self.assertEqual(list(VALIDATOR.iter_errors(entry)), [])
        tutorials = entry.get("tutorials", [])
        self.assertTrue(tutorials)
        self.assertTrue(all(item["type"] == "article" for item in tutorials))
        self.assertTrue(all(urlparse(item["url"]).scheme == "https" for item in tutorials))
        self.assertTrue(any("no verified official" in note.lower() for note in entry["notes"] + tutorials[0].get("notes", [])))

    def test_usb_media_tools_have_official_sources_and_destructive_warnings(self):
        for filename in (
            "rufus-bootable-usb-writer.json",
            "balena-etcher-usb-image-writer.json",
            "ventoy-multiboot-usb.json",
            "windows-media-creation-tool.json",
        ):
            entry = self.load_entry(filename)
            self.assertEqual(list(VALIDATOR.iter_errors(entry)), [], filename)
            self.assertTrue(entry["source"]["url"].startswith("https://"))
            self.assertTrue(any("usb" in note.lower() and ("erase" in note.lower() or "format" in note.lower() or "delete" in note.lower()) for note in entry.get("notes", [])), filename)

    def test_recovery_page_renders_video_and_missing_video_notice(self):
        page = (ROOT / "frontend/software-os-center.html").read_text(encoding="utf-8")
        self.assertIn("youtube-nocookie.com/embed/", page)
        self.assertIn("No verified official recovery video is listed yet", page)
        self.assertIn("entry.tutorials", page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
