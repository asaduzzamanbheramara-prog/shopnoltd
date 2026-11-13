#!/usr/bin/env python3
"""Export referenced GitHub Actions secrets into a private, short-lived JSON file.

The JSON is encrypted by the caller before it is copied to the backup branch.
Secret values are never printed. BACKUP_ENCRYPTION_KEY is deliberately excluded:
it must remain in an independent password manager/offline recovery copy.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ALLOWLIST = (
    "KEYCLOAK_AUDIT_CLIENT_ID",
    "KEYCLOAK_AUDIT_CLIENT_SECRET",
    "KEYCLOAK_E2E_CLIENT_ID",
    "KEYCLOAK_E2E_CLIENT_SECRET",
    "SHOPNOLTD_ADMIN_USERNAME",
    "SHOPNOLTD_ADMIN_PASSWORD",
    "SHOPNOLTD_OWNER_USERNAME",
    "SHOPNOLTD_OWNER_PASSWORD",
    "SHOPNOLTD_USER_USERNAME",
    "SHOPNOLTD_USER_PASSWORD",
    "SHOPNOLTD_ADMIN_TOTP_SECRET",
    "SHOPNOLTD_OWNER_TOTP_SECRET",
    "SHOPNOLTD_USER_TOTP_SECRET",
    "MAIL_SMTP_USERNAME",
    "MAIL_SMTP_PASSWORD",
    "MAIL_SMTP_ENVELOPE_FROM",
    # Referenced by the code-server Continue config template.
    "CODE_SERVER_LITELLM_API_KEY",
)
EXCLUDED = {"BACKUP_ENCRYPTION_KEY", "GITHUB_TOKEN"}
SECRET_REF = re.compile(r"secrets\.([A-Z0-9_]+)")


def check_workflow_coverage() -> set[str]:
    workflow_dir = Path(".github/workflows")
    refs: set[str] = set()
    if not workflow_dir.is_dir():
        raise SystemExit("ERROR: .github/workflows is missing.")
    for path in sorted(workflow_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".yml", ".yaml"}:
            refs.update(SECRET_REF.findall(path.read_text(encoding="utf-8")))
    uncovered = sorted(refs - set(ALLOWLIST) - EXCLUDED)
    if uncovered:
        raise SystemExit(
            "ERROR: add these workflow secret references to the encrypted backup allowlist: "
            + ", ".join(uncovered)
        )
    return refs


def write_private_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        stream.write("\n")
    os.chmod(path, 0o600)


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--check-only":
        refs = check_workflow_coverage()
        print(
            "PASS: all workflow secret references are covered "
            f"({len(refs - EXCLUDED)} backed-up names; key and ephemeral token excluded)."
        )
        return 0
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: export-github-actions-secrets.py <private-json-output> <inventory-csv-output>"
        )

    refs = check_workflow_coverage()
    captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    values = {name: os.environ[name] for name in ALLOWLIST if os.environ.get(name, "") != ""}
    inventory_path = Path(sys.argv[2])
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    with inventory_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("secret_name", "configured"))
        for name in ALLOWLIST:
            writer.writerow((name, "yes" if name in values else "no"))
    os.chmod(inventory_path, 0o600)

    if not values:
        inventory_path.unlink(missing_ok=True)
        raise SystemExit("ERROR: no configured GitHub Actions secrets were available to escrow.")

    payload = {
        "schema_version": 1,
        "captured_at": captured_at,
        "source": "GitHub Actions secret context",
        "secrets": values,
    }
    write_private_json(Path(sys.argv[1]), payload)
    print(
        f"Captured {len(values)} configured GitHub Actions secrets; "
        f"{len(ALLOWLIST) - len(values)} allowlisted names are unset. Values were not logged."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
