#!/usr/bin/env python3
"""Offline integrity checker for a file and a publisher-sourced digest.

This tool never downloads, executes, installs, or writes to the artifact. The
expected digest must be obtained independently from the publisher's trusted
release page or signature-verified metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import re
import sys
from pathlib import Path

DIGEST_LENGTHS = {"sha256": 64, "sha512": 128}


def verify_file(path: Path, algorithm: str, expected: str) -> bool:
    """Return whether path's digest matches a well-formed expected digest."""
    if algorithm not in DIGEST_LENGTHS:
        raise ValueError("unsupported algorithm")
    if not re.fullmatch(r"[0-9a-fA-F]+", expected or "") or len(expected) != DIGEST_LENGTHS[algorithm]:
        raise ValueError(f"expected {algorithm} digest must be {DIGEST_LENGTHS[algorithm]} hexadecimal characters")
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return hmac.compare_digest(digest.hexdigest().lower(), expected.lower())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="local file to verify; it will not be modified")
    parser.add_argument("--algorithm", choices=sorted(DIGEST_LENGTHS), required=True)
    parser.add_argument("--expected", required=True, help="publisher-sourced SHA-256 or SHA-512 digest")
    args = parser.parse_args(argv)
    try:
        valid = verify_file(args.file, args.algorithm, args.expected)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if valid:
        print(f"PASS: {args.file.name} matches the supplied {args.algorithm} digest")
        return 0
    print(f"FAIL: {args.file.name} does not match the supplied {args.algorithm} digest", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
