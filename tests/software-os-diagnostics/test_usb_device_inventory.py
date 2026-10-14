"""Tests for read-only USB inventory parsing; no host devices are touched."""
from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/software-os-diagnostics"))
from usb_device_inventory import parse_lsblk  # noqa: E402


class UsbInventoryTests(unittest.TestCase):
    def test_only_removable_whole_disks_are_candidates(self):
        payload = {"blockdevices": [
            {"name": "sda", "path": "/dev/sda", "type": "disk", "rm": False, "size": 500000000000, "model": "Internal"},
            {"name": "sdb", "path": "/dev/sdb", "type": "disk", "rm": True, "size": 32000000000, "model": "USB Stick", "tran": "usb", "maj:min": "8:16"},
            {"name": "sdb1", "path": "/dev/sdb1", "type": "part", "rm": True, "size": 31000000000, "model": "USB Stick"},
            {"name": "sdc", "path": "/dev/sdc", "type": "disk", "rm": True, "size": 0, "model": "Bad"},
        ]}
        found = parse_lsblk(payload)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["path"], "/dev/sdb")
        self.assertFalse(found[0]["write_authorized"])
        self.assertTrue(found[0]["candidate_only"])

    def test_missing_or_invalid_blockdevices_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_lsblk({})
        with self.assertRaises(ValueError):
            parse_lsblk({"blockdevices": "unexpected"})

    def test_unknown_model_is_handled(self):
        found = parse_lsblk({"blockdevices": [
            {"type": "disk", "rm": "1", "size": 1024}
        ]})
        self.assertEqual(found[0]["model"], "Unknown model")
        self.assertIsNone(found[0]["path"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
