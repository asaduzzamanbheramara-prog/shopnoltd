#!/usr/bin/env python3
"""Read-only removable-drive inventory for recovery-media planning.

This helper queries native OS inventory tools only. It never opens a block device
for writing, formats media, downloads images, or changes partitions. A candidate
is only a hint and is never authorized for destructive writes.
"""
from __future__ import annotations

import argparse
import json
import plistlib
import shutil
import subprocess
import sys
from typing import Any


def _candidate(path: str | None, model: str, size: int, transport: str | None,
               identifier: str | None = None) -> dict[str, Any]:
    return {
        "path": path,
        "model": model.strip() or "Unknown model",
        "size_bytes": size,
        "transport": transport,
        "identifier": identifier,
        "candidate_only": True,
        "write_authorized": False,
    }


def parse_lsblk(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return Linux removable whole-disk candidates; never infer write authorization."""
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
        candidates.append(_candidate(
            device.get("path") if isinstance(device.get("path"), str) else None,
            str(device.get("model") or "Unknown model"),
            size,
            device.get("tran") if isinstance(device.get("tran"), str) else None,
            device.get("maj:min") if isinstance(device.get("maj:min"), str) else None,
        ))
    return candidates


def parse_windows_inventory(payload: Any) -> list[dict[str, Any]]:
    """Parse PowerShell CIM output, accepting only explicitly USB-identified disks."""
    if payload is None:
        return []
    devices = payload if isinstance(payload, list) else [payload]
    candidates: list[dict[str, Any]] = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        pnp_id = str(device.get("PNPDeviceID") or "")
        interface = str(device.get("InterfaceType") or "")
        if interface.casefold() != "usb" and not pnp_id.upper().startswith(("USB\\\\", "USBSTOR\\\\")):
            continue
        size = device.get("Size")
        index = device.get("Index")
        if not isinstance(size, (int, float)) or size <= 0 or not isinstance(index, (int, float)):
            continue
        model = str(device.get("Model") or "Unknown model")
        candidates.append(_candidate(
            f"\\\\.\\PHYSICALDRIVE{int(index)}", model, int(size), "usb", pnp_id or None
        ))
    return candidates


def parse_macos_inventory(whole_disks: Any, disk_info_by_id: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse diskutil metadata; only external USB/removable whole disks are candidates."""
    if not isinstance(whole_disks, list):
        raise ValueError("diskutil output is missing a WholeDisks list")
    candidates: list[dict[str, Any]] = []
    for disk_id in whole_disks:
        if not isinstance(disk_id, str) or not disk_id or "/" in disk_id:
            continue
        info = disk_info_by_id.get(disk_id)
        if not isinstance(info, dict) or info.get("Internal") is True:
            continue
        protocol = str(info.get("BusProtocol") or info.get("Protocol") or "").casefold()
        removable = info.get("RemovableMedia") is True
        if protocol != "usb" and not removable:
            continue
        size = info.get("TotalSize")
        if not isinstance(size, (int, float)) or size <= 0:
            continue
        path = info.get("DeviceNode")
        if not isinstance(path, str) or not path.startswith("/dev/"):
            path = f"/dev/{disk_id}"
        candidates.append(_candidate(
            path, str(info.get("MediaName") or info.get("IORegistryEntryName") or "Unknown model"),
            int(size), protocol or ("removable" if removable else None), disk_id,
        ))
    return candidates


def _run_json(command: list[str], *, timeout: int = 10) -> Any:
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    return json.loads(result.stdout)


def inventory_linux() -> list[dict[str, Any]]:
    if shutil.which("lsblk") is None:
        raise RuntimeError("Required command 'lsblk' was not found")
    return parse_lsblk(_run_json([
        "lsblk", "--bytes", "--json", "--output", "NAME,PATH,TYPE,RM,SIZE,MODEL,TRAN,MAJ:MIN"
    ]))


def inventory_windows() -> list[dict[str, Any]]:
    powershell = shutil.which("pwsh") or shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell is None:
        raise RuntimeError("PowerShell was not found")
    script = (
        "Get-CimInstance Win32_DiskDrive | "
        "Select-Object Index,Model,Size,InterfaceType,MediaType,PNPDeviceID | "
        "ConvertTo-Json -Compress"
    )
    return parse_windows_inventory(_run_json([
        powershell, "-NoProfile", "-NonInteractive", "-Command", script
    ]))


def inventory_macos() -> list[dict[str, Any]]:
    if shutil.which("diskutil") is None:
        raise RuntimeError("Required command 'diskutil' was not found")
    listing = subprocess.run(
        ["diskutil", "list", "-plist"], check=True, capture_output=True, timeout=10
    )
    payload = plistlib.loads(listing.stdout)
    whole_disks = payload.get("WholeDisks") if isinstance(payload, dict) else None
    if not isinstance(whole_disks, list):
        raise ValueError("diskutil output is missing a WholeDisks list")
    details: dict[str, Any] = {}
    for disk_id in whole_disks:
        if not isinstance(disk_id, str) or not disk_id or "/" in disk_id:
            continue
        info = subprocess.run(
            ["diskutil", "info", "-plist", disk_id], check=True,
            capture_output=True, timeout=10
        )
        details[disk_id] = plistlib.loads(info.stdout)
    return parse_macos_inventory(whole_disks, details)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    platform = sys.platform
    try:
        if platform == "linux":
            candidates, platform_name = inventory_linux(), "linux"
        elif platform == "win32":
            candidates, platform_name = inventory_windows(), "windows"
        elif platform == "darwin":
            candidates, platform_name = inventory_macos(), "macos"
        else:
            print("Unsupported platform; no devices were changed.", file=sys.stderr)
            return 3
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, plistlib.InvalidFileException,
            ValueError, RuntimeError) as exc:
        print(f"Could not safely inventory devices: {exc}", file=sys.stderr)
        return 2

    warning = (
        "Candidates are hints only. Independently verify device identity and capacity; "
        "this tool never authorizes or performs writes."
    )
    payload = {
        "mode": "read-only",
        "platform": platform_name,
        "candidates": candidates,
        "warning": warning,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(warning)
        if not candidates:
            print("No removable USB whole-disk candidates were reported.")
        for item in candidates:
            print(f"{item['path'] or '(path unavailable)'} | {item['model']} | "
                  f"{item['size_bytes']} bytes | transport={item['transport'] or 'unknown'}")
        print("No disk was opened for writing or modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
