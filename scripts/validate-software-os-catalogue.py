#!/usr/bin/env python3
"""Validate all Shopnoltd catalogue metadata without executing downloaded content."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "catalogue/schema/software-entry.schema.json"
ENTRIES_DIR = ROOT / "catalogue/entries"


def main() -> int:
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        entry_paths = sorted(ENTRIES_DIR.glob("*.json"))
        if not entry_paths:
            print(f"ERROR: no catalogue JSON entries found in {ENTRIES_DIR}", file=sys.stderr)
            return 1
        entries = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in entry_paths]
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: unable to read schema/catalogue JSON: {exc}", file=sys.stderr)
        return 1

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    failed = False
    for path, entry in entries:
        errors = sorted(validator.iter_errors(entry), key=lambda err: list(map(str, err.path)))
        if errors:
            failed = True
            for error in errors:
                field_path = ".".join(map(str, error.absolute_path)) or "<root>"
                print(f"ERROR {path.relative_to(ROOT)}:{field_path}: {error.message}", file=sys.stderr)
        else:
            print(f"OK: {path.relative_to(ROOT)} validates against {SCHEMA_PATH.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
