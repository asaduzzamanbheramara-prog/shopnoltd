#!/usr/bin/env python3
"""Generate a non-destructive bootable-USB preparation checklist.

This planner never enumerates, formats, partitions, or writes to physical disks.
It does not download images or assert that a particular image supports a device.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Literal

TargetOS = Literal["windows", "linux", "other"]
Architecture = Literal["x86_64", "arm64", "x86", "other"]
Firmware = Literal["uefi", "legacy-bios", "unknown"]
Goal = Literal["repair", "rescue-data", "install"]


@dataclass(frozen=True)
class RecoveryPlan:
    target_os: str
    architecture: str
    firmware: str
    secure_boot: str
    goal: str
    usb_capacity_gib: int
    image_verified: bool
    status: str
    checklist: list[str]
    warnings: list[str]


def build_plan(
    target_os: TargetOS,
    architecture: Architecture,
    firmware: Firmware,
    secure_boot: Literal["enabled", "disabled", "unknown"],
    goal: Goal,
    usb_capacity_gib: int,
    image_verified: bool,
) -> RecoveryPlan:
    """Build a conservative checklist; no destructive or device I/O occurs."""
    if usb_capacity_gib < 1:
        raise ValueError("USB capacity must be a positive number of GiB")

    checklist = [
        "Use a separate working computer or an already available recovery environment.",
        "Choose an image from the operating-system publisher or the exact device vendor.",
        "Check the publisher's signature/checksum source independently; a matching digest alone does not prove source authenticity.",
        "Read the image's minimum capacity, architecture, firmware, and Secure Boot requirements.",
        "Back up important data before attempting repair or reinstall.",
        "Use a trusted USB-writing tool documented by the image publisher.",
        "Before writing, identify the physical USB drive by model and capacity; do not guess from drive letters alone.",
        "Show a final warning that writing the image usually erases the selected USB, then require a separate explicit confirmation.",
        "After writing, verify the media and test boot where possible; VM tests do not guarantee physical-device compatibility.",
    ]
    warnings: list[str] = []
    if not image_verified:
        warnings.append("Image verification is incomplete: do not write the image to USB until a trusted publisher digest/signature has been checked.")
    if architecture == "other":
        warnings.append("Target architecture is unspecified or uncommon; verify exact image support before proceeding.")
    if firmware == "unknown":
        warnings.append("Firmware mode is unknown; confirm UEFI versus legacy BIOS and partition-scheme requirements.")
    if secure_boot == "unknown":
        warnings.append("Secure Boot compatibility is unknown; verify the image publisher's instructions.")
    if usb_capacity_gib < 8:
        warnings.append("USB capacity is below 8 GiB; many current OS images require more space. Check the exact image requirement.")
    if target_os == "other":
        warnings.append("Use only the device vendor's documented recovery process; a generic PC ISO may not be compatible.")
    if goal == "install":
        warnings.append("OS installation can erase data or partitions. Confirm the target disk separately and back up data first.")
    elif goal == "rescue-data":
        warnings.append("Prefer a read-only/live rescue workflow and copy recovered data to a different physical drive.")
    elif goal == "repair":
        warnings.append("Try documented non-destructive startup repair before any reset, repartition, or reinstall.")
    if target_os == "windows" and architecture == "arm64":
        warnings.append("Confirm the exact Windows-on-ARM image and device support; x64 media is not interchangeable.")
    status = "blocked-pending-image-verification" if not image_verified else ("review-required" if warnings else "checklist-ready")
    return RecoveryPlan(
        target_os, architecture, firmware, secure_boot, goal, usb_capacity_gib,
        image_verified, status, checklist, warnings,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-os", choices=["windows", "linux", "other"], required=True)
    parser.add_argument("--architecture", choices=["x86_64", "arm64", "x86", "other"], required=True)
    parser.add_argument("--firmware", choices=["uefi", "legacy-bios", "unknown"], required=True)
    parser.add_argument("--secure-boot", choices=["enabled", "disabled", "unknown"], required=True)
    parser.add_argument("--goal", choices=["repair", "rescue-data", "install"], required=True)
    parser.add_argument("--usb-capacity-gib", type=int, required=True)
    parser.add_argument("--image-verified", action="store_true", help="only if publisher digest/signature was independently checked")
    args = parser.parse_args(argv)
    try:
        plan = build_plan(
            args.target_os, args.architecture, args.firmware, args.secure_boot,
            args.goal, args.usb_capacity_gib, args.image_verified,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(asdict(plan), indent=2))
    return 0 if plan.image_verified else 2


if __name__ == "__main__":
    raise SystemExit(main())
