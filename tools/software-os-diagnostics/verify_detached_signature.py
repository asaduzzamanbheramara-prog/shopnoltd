#!/usr/bin/env python3
"""Verify a local OpenPGP detached signature against an explicitly trusted keyring.

This checker is offline and read-only with respect to the image/signature. The
keyring and expected fingerprint must be obtained and checked independently
through the publisher's trusted distribution channel.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

FINGERPRINT_RE = re.compile(r"^(?:[0-9A-Fa-f]{40}|[0-9A-Fa-f]{64})$")


def verify_detached_signature(
    artifact: Path,
    signature: Path,
    keyring: Path,
    expected_fingerprint: str,
    *,
    gpgv_path: str | None = None,
    timeout: int = 30,
) -> tuple[bool, str]:
    """Return (verified, reason); require both a valid signature and expected signer."""
    expected = (expected_fingerprint or "").replace(" ", "").upper()
    if not FINGERPRINT_RE.fullmatch(expected):
        raise ValueError("expected fingerprint must be a 40- or 64-character hexadecimal fingerprint")
    for label, path in (("artifact", artifact), ("signature", signature), ("trusted keyring", keyring)):
        if not path.is_file():
            raise ValueError(f"{label} file does not exist or is not a regular file")

    executable = gpgv_path or shutil.which("gpgv")
    if not executable:
        raise RuntimeError("gpgv is required but was not found")
    result = subprocess.run(
        [executable, "--status-fd=1", "--keyring", str(keyring), str(signature), str(artifact)],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    status_lines = [
        line for line in result.stdout.splitlines()
        if line.startswith("[GNUPG:] ")
    ]
    valid_signers: set[str] = set()
    for line in status_lines:
        fields = line.split()
        if len(fields) >= 3 and fields[1] == "VALIDSIG":
            # GnuPG includes the signing-key fingerprint first and, for a
            # signing subkey, the primary-key fingerprint as the final field.
            valid_signers.add(fields[2].upper())
            if len(fields) >= 12 and FINGERPRINT_RE.fullmatch(fields[-1]):
                valid_signers.add(fields[-1].upper())

    if result.returncode != 0 or not valid_signers:
        return False, "signature verification failed against the supplied keyring"
    if expected not in valid_signers:
        return False, "signature is valid, but the signer fingerprint does not match the expected publisher key"
    return True, "valid OpenPGP signature from the expected fingerprint"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="local artifact file; never modified")
    parser.add_argument("signature", type=Path, help="local detached OpenPGP signature file")
    parser.add_argument("--keyring", type=Path, required=True, help="trusted local OpenPGP keyring")
    parser.add_argument("--expected-fingerprint", required=True, help="publisher fingerprint verified out of band")
    args = parser.parse_args(argv)
    try:
        valid, message = verify_detached_signature(
            args.artifact, args.signature, args.keyring, args.expected_fingerprint
        )
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not valid:
        print(f"FAIL: {message}", file=sys.stderr)
        return 1
    print(f"PASS: {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
