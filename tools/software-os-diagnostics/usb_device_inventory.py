#!/usr/bin/env python3
"""Read-only removable-drive inventory for recovery-media planning.

This helper only queries Linux lsblk. It never opens a block device for writing,
formats media, downloads images, or changes partitions. Removable flags are hints,
not proof that a device is safe to overwrite.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any


def parse_lsblk(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return removable whole-disk candidates; never infer write authorization."""
    devices = payload.get("blockdevices")
    if not isinstance(devices, list):
        raise ValueError("lsblk output is missing a blockdevices list")
    candidates: list[dict[str, Any]] = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        if device.get("type") != "disk" or str(device.get("rm", "0")) not in ("1", "true", "True"):
            continue
        size = device.get("size")
        if not isinstance(size, int) or size <= 0:
            continue
        candidates.append({
            "path": device.get("path") if isinstance(device.get("path"), str) else None,
            "model": (device.get("model") or "").strip() or "Unknown model",
            "size_bytes": size,
            "transport": device.get("tran") if isinstance(device.get("tran"), str) else None,
            "major_minor": device.get("maj:min") if isinstance(device.get("maj:min"), str) else None,
            "candidate_only": True,
            "write_authorized": False,
        })
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    if sys.platform != "linux":
        print("This read-only inventory currently supports Linux only; no devices were changed.", file=sys.stderr)
        return 3
    if shutil.which("lsblk") is None:
        print("Required command 'lsblk' was not found; no devices were changed.", file=sys.stderr)
        return 3
    try:
        result = subprocess.run(
            ["lsblk", "--bytes", "--json", "--output", "NAME,PATH,TYPE,RM,SIZE,MODEL,TRAN,MAJ:MIN"],
            check=True, capture_output=True, text=True, timeout=10,
        )
        candidates = parse_lsblk(json.loads(result.stdout))
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError) as exc:
        print(f"Could not safely inventory devices: {exc}", file=sys.stderr)
        return 2
    payload = {
        "mode": "read-only",
        "platform": "linux",
        "candidates": candidates,
        "warning": "Candidates are hints only. Verify device identity physically; this tool never authorizes or performs writes.",
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(payload["warning"])
        if not candidates:
            print("No removable whole-disk candidates were reported.")
        for item in candidates:
            print(f"{item['path'] or '(path unavailable)'} | {item['model']} | {item['size_bytes']} bytes | transport={item['transport'] or 'unknown'}")
        print("No disk was opened for writing or modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
