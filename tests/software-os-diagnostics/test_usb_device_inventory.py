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


    def test_windows_inventory_only_reports_explicit_usb_disks(self):
        from usb_device_inventory import parse_windows_inventory

        found = parse_windows_inventory([
            {"Index": 0, "Model": "Internal SSD", "Size": 512000, "InterfaceType": "SCSI", "PNPDeviceID": "SCSI\\DISK"},
            {"Index": 2, "Model": "USB Stick", "Size": 32000000000, "InterfaceType": "USB", "PNPDeviceID": "USB\\VID_1234"},
            {"Index": 3, "Model": "Unknown", "Size": 0, "InterfaceType": "USB", "PNPDeviceID": "USB\\VID_9999"},
            {"Index": 4, "Model": "USB Storage", "Size": 16000000000, "InterfaceType": "SCSI", "PNPDeviceID": "USBSTOR\\DISK&VEN_TEST"},
        ])
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["path"], r"\\.\PHYSICALDRIVE2")
        self.assertEqual(found[0]["transport"], "usb")
        self.assertEqual(found[1]["path"], r"\\.\PHYSICALDRIVE4")
        self.assertEqual(found[1]["transport"], "usb")
        self.assertFalse(any(item["write_authorized"] for item in found))

    def test_macos_inventory_excludes_internal_and_unknown_disks(self):
        from usb_device_inventory import parse_macos_inventory

        found = parse_macos_inventory(
            ["disk0", "disk2", "disk3"],
            {
                "disk0": {"Internal": True, "BusProtocol": "Apple Fabric", "TotalSize": 500000000000},
                "disk2": {"Internal": False, "BusProtocol": "USB", "TotalSize": 32000000000,
                          "MediaName": "External USB", "DeviceNode": "/dev/disk2"},
                "disk3": {"Internal": False, "BusProtocol": "Thunderbolt", "TotalSize": 1000000000},
            },
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["path"], "/dev/disk2")
        self.assertEqual(found[0]["model"], "External USB")
        self.assertFalse(found[0]["write_authorized"])

    def test_malformed_cross_platform_inventory_fails_closed(self):
        from usb_device_inventory import parse_macos_inventory, parse_windows_inventory

        self.assertEqual(parse_windows_inventory({"unexpected": "shape"}), [])
        with self.assertRaises(ValueError):
            parse_macos_inventory({"not": "a list"}, {})

    def test_unknown_model_is_handled(self):
        found = parse_lsblk({"blockdevices": [
            {"type": "disk", "rm": "1", "size": 1024}
        ]})
        self.assertEqual(found[0]["model"], "Unknown model")
        self.assertIsNone(found[0]["path"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
