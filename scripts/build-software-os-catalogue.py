#!/usr/bin/env python3
"""Build a browser-safe JSON catalogue from schema-validated metadata entries."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRIES_DIR = ROOT / "catalogue/entries"
OUTPUT = ROOT / "frontend/catalogue.json"


def main() -> int:
    try:
        paths = sorted(ENTRIES_DIR.glob("*.json"))
        if not paths:
            raise ValueError("no catalogue entries found")
        entries = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        OUTPUT.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: cannot build catalogue: {exc}", file=sys.stderr)
        return 1
    print(f"Built {len(entries)} catalogue entries into {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
