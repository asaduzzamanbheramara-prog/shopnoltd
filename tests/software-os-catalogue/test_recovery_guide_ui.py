"""Regression tests for the browser-only recovery guide."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = (ROOT / "frontend/software-os-center.html").read_text(encoding="utf-8")


class RecoveryGuideUITests(unittest.TestCase):
    def test_guided_planner_exposes_device_os_and_goal_choices(self):
        for token in (
            'id="recovery-device"', 'id="recovery-os"', 'id="recovery-goal"',
            'id="recovery-firmware"', 'id="build-recovery-guide"',
        ):
            with self.subTest(token=token):
                self.assertIn(token, PAGE)

    def test_non_pc_devices_get_vendor_specific_guidance(self):
        self.assertIn("Do not assume a generic PC bootable USB can recover this device.", PAGE)
        self.assertIn("Apple’s documented recovery/update workflow", PAGE)
        self.assertIn("do not flash firmware from a similar-looking model", PAGE)

    def test_ui_discloses_no_disk_io_and_usb_data_loss_risk(self):
        self.assertIn("does not download images, inspect connected drives, or write a pendrive", PAGE)
        self.assertIn("writing usually erases that USB", PAGE)
        self.assertIn("It does not download, verify, install, or write any image.", PAGE)

    def test_reinstall_and_data_rescue_have_separate_warnings(self):
        self.assertIn("Prefer a data-preserving or read-only rescue path first", PAGE)
        self.assertIn("Reinstall/factory recovery can erase data.", PAGE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
