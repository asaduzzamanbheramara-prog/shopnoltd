"""Regression tests for the non-destructive recovery media planner."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/software-os-diagnostics"))
import recovery_media_plan  # noqa: E402


class RecoveryMediaPlanTests(unittest.TestCase):
    def test_unverified_image_blocks_writing(self):
        plan = recovery_media_plan.build_plan(
            "linux", "x86_64", "uefi", "enabled", "repair", 16, False
        )
        self.assertEqual(plan.status, "blocked-pending-image-verification")
        self.assertTrue(any("do not write" in warning for warning in plan.warnings))

    def test_install_goal_warns_about_data_loss(self):
        plan = recovery_media_plan.build_plan(
            "windows", "x86_64", "uefi", "enabled", "install", 32, True
        )
        self.assertTrue(any("erase data" in warning for warning in plan.warnings))

    def test_unknown_firmware_and_secure_boot_are_flagged(self):
        plan = recovery_media_plan.build_plan(
            "linux", "x86_64", "unknown", "unknown", "rescue-data", 16, True
        )
        self.assertTrue(any("UEFI versus legacy BIOS" in warning for warning in plan.warnings))
        self.assertTrue(any("Secure Boot" in warning for warning in plan.warnings))

    def test_small_usb_capacity_is_flagged(self):
        plan = recovery_media_plan.build_plan(
            "linux", "x86_64", "uefi", "disabled", "repair", 4, True
        )
        self.assertTrue(any("below 8 GiB" in warning for warning in plan.warnings))

    def test_invalid_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            recovery_media_plan.build_plan(
                "linux", "x86_64", "uefi", "enabled", "repair", 0, True
            )

    def test_cli_returns_nonzero_for_unverified_image_and_json(self):
        command = [
            sys.executable, str(ROOT / "tools/software-os-diagnostics/recovery_media_plan.py"),
            "--target-os", "linux", "--architecture", "x86_64",
            "--firmware", "uefi", "--secure-boot", "enabled",
            "--goal", "repair", "--usb-capacity-gib", "16",
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "blocked-pending-image-verification")


if __name__ == "__main__":
    unittest.main(verbosity=2)
