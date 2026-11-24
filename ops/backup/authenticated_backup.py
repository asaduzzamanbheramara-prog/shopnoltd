#!/usr/bin/env python3
"""Create/verify encrypt-then-MAC sidecars for Shopnoltd OpenSSL backups."""
from __future__ import annotations
import argparse
import hashlib
import hmac
import os
from pathlib import Path

ITERATIONS = 600_000
CONTEXT = b"Shopnoltd authenticated backup integrity v1\0"
MAGIC = b"Salted__"


def mac_key(ciphertext: bytes, password: str) -> bytes:
    if len(ciphertext) < 16 or ciphertext[:8] != MAGIC:
        raise ValueError("Unsupported or malformed OpenSSL salted ciphertext")
    salt = ciphertext[8:16]
    return hashlib.pbkdf2_hmac("sha256", password.encode(), CONTEXT + salt, ITERATIONS, dklen=32)


def create(path: Path, password: str) -> None:
    data = path.read_bytes()
    digest = hmac.new(mac_key(data, password), data, hashlib.sha256).hexdigest()
    path.with_name(path.name + ".hmac").write_text(digest + "\n", encoding="ascii")


def verify(path: Path, password: str) -> None:
    data = path.read_bytes()
    expected = path.with_name(path.name + ".hmac").read_text(encoding="ascii").strip()
    actual = hmac.new(mac_key(data, password), data, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, actual):
        raise SystemExit(f"HMAC verification failed: {path.name}")
    print(f"PASS: authenticated integrity verified for {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("create", "verify"))
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    password = os.environ.get("BACKUP_ENCRYPTION_KEY", "")
    if not password:
        raise SystemExit("BACKUP_ENCRYPTION_KEY is required")
    for path in args.files:
        (create if args.mode == "create" else verify)(path, password)


if __name__ == "__main__":
    main()
