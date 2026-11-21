#!/usr/bin/env python3
"""Publish encrypted Shopnoltd backup artifacts to a private GitHub repository."""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
FILES = (
    "latest.dump.enc",
    "latest.dump.enc.sha256",
    "latest.dump.enc.hmac",
    "latest.all-databases.tar.gz.enc",
    "latest.all-databases.tar.gz.enc.sha256",
    "latest.all-databases.tar.gz.enc.hmac",
    "latest.kubernetes-secrets.json.enc",
    "latest.kubernetes-secrets.json.enc.sha256",
    "latest.kubernetes-secrets.json.enc.hmac",
    "timestamp.txt",
    "source-revision.txt",
)
README = """# Shopnoltd encrypted database and Kubernetes Secrets backups

This private repository branch contains encrypted PostgreSQL database dumps,
global roles, and the all-namespace Kubernetes Secret export. Each encrypted
artifact has SHA-256 and keyed HMAC-SHA256 sidecars. The encryption key is
supplied at runtime through BACKUP_ENCRYPTION_KEY and is never stored here.

Never publish or apply decrypted files casually. Restore is a manual,
reviewed disaster-recovery operation. Preserve GitHub Actions secret values
and the encryption key separately in a secure password manager.
"""


class GitHubAPIError(RuntimeError):
    pass


def api(token: str, method: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "Shopnoltd-Encrypted-Backup",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        raise GitHubAPIError(f"GitHub API {method} {path} failed ({exc.code}): {detail}") from None


def main() -> int:
    repo = os.environ["BACKUP_REPOSITORY"]
    token = os.environ["BACKUP_REPOSITORY_TOKEN"]
    branch = os.environ.get("BACKUP_BRANCH", "database-backups")
    workdir = pathlib.Path(os.environ.get("BACKUP_WORKDIR", "/tmp/shopnoltd-dr-backup"))
    if "/" not in repo or repo == os.environ.get("GITHUB_REPOSITORY"):
        raise SystemExit("Backup repository must be a separate owner/repository destination.")

    destination = api(token, "GET", f"/repos/{repo}")
    if destination.get("private") is not True:
        raise SystemExit("Refusing to publish: destination repository is not private.")

    entries = []
    for filename in FILES:
        path = workdir / filename
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"Required encrypted backup artifact is missing or empty: {filename}")
        size = path.stat().st_size
        if size > 90 * 1024 * 1024:
            raise SystemExit(f"{filename} exceeds the safe GitHub Git Database API limit (90 MiB).")
        blob = api(token, "POST", f"/repos/{repo}/git/blobs", {
            "content": base64.b64encode(path.read_bytes()).decode("ascii"),
            "encoding": "base64",
        })
        entries.append({"path": f"backup/{filename}", "mode": "100644", "type": "blob", "sha": blob["sha"]})

    readme_blob = api(token, "POST", f"/repos/{repo}/git/blobs", {
        "content": base64.b64encode(README.encode()).decode("ascii"),
        "encoding": "base64",
    })
    entries.append({"path": "backup/README.md", "mode": "100644", "type": "blob", "sha": readme_blob["sha"]})

    # Keep each backup commit based on the previous backup branch; initialize from main.
    branch_exists = True
    try:
        ref = api(token, "GET", f"/repos/{repo}/git/ref/heads/{branch}")
        parent_sha = ref["object"]["sha"]
    except GitHubAPIError as exc:
        if "(404)" not in str(exc):
            raise
        branch_exists = False
        main_ref = api(token, "GET", f"/repos/{repo}/git/ref/heads/main")
        parent_sha = main_ref["object"]["sha"]

    parent = api(token, "GET", f"/repos/{repo}/git/commits/{parent_sha}")
    tree = api(token, "POST", f"/repos/{repo}/git/trees", {
        "base_tree": parent["tree"]["sha"],
        "tree": entries,
    })
    commit = api(token, "POST", f"/repos/{repo}/git/commits", {
        "message": "backup: encrypted PostgreSQL and Kubernetes Secrets snapshot",
        "tree": tree["sha"],
        "parents": [parent_sha],
    })

    if branch_exists:
        api(token, "PATCH", f"/repos/{repo}/git/refs/heads/{branch}", {
            "sha": commit["sha"],
            "force": True,
        })
    else:
        api(token, "POST", f"/repos/{repo}/git/refs", {
            "ref": f"refs/heads/{branch}",
            "sha": commit["sha"],
        })

    print(f"PASS: published {len(entries)} encrypted backup metadata/artifact files.")
    print(f"PASS: private repository {repo}, branch {branch}, commit {commit['sha']}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GitHubAPIError, KeyError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
