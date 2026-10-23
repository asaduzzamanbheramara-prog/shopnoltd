#!/usr/bin/env python3
"""Validate recovery-image manifest metadata; never downloads or writes images."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "catalogue/schema/recovery-image-manifest.schema.json"


def validate_manifest(path: Path) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(manifest), key=lambda error: list(map(str, error.absolute_path)))
    return [
        f"${'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
        for error in errors
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to a recovery image manifest JSON file")
    args = parser.parse_args()
    try:
        errors = validate_manifest(args.manifest)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Cannot read manifest: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Manifest schema valid: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
