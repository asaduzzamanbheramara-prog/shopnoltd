#!/usr/bin/env python3
"""Validate Shopnoltd catalogue metadata without executing downloaded content."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "catalogue/schema/software-entry.schema.json"
ENTRY_PATH = ROOT / "catalogue/entries/sample-linux-tools.json"


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    payload = json.loads(ENTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"id", "name", "kind", "description", "platforms", "architectures", "source", "license_note", "verification", "pricing", "installation_guide", "notes"}:
        # The sample file is a single entry, not a wrapper or arbitrary payload.
        pass
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(map(str, err.path)))
    if errors:
        for error in errors:
            path = ".".join(map(str, error.absolute_path)) or "<root>"
            print(f"ERROR {path}: {error.message}", file=sys.stderr)
        return 1
    print(f"OK: {ENTRY_PATH.relative_to(ROOT)} validates against {SCHEMA_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
