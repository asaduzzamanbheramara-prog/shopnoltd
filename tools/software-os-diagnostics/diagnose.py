#!/usr/bin/env python3
"""Read-only, offline diagnostics starter for the Shopnoltd Software & OS Center.

This utility reports a small allow-list of general system facts. It does not
read user files, inspect credentials, make network requests, install software,
or change system settings.
"""
from __future__ import annotations

import json
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

VERSION = "0.1.0"


def collect_report(home: Path | None = None) -> dict[str, Any]:
    """Collect minimal diagnostics without exposing filesystem paths."""
    home_path = home if home is not None else Path.home()
    usage = shutil.disk_usage(home_path)
    return {
        "tool": "shopnoltd-read-only-diagnostics",
        "tool_version": VERSION,
        "os_family": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "home_volume_total_bytes": usage.total,
        "home_volume_free_bytes": usage.free,
        "mode": "read-only-offline",
        "actions_performed": [],
    }


def main() -> int:
    print(json.dumps(collect_report(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
