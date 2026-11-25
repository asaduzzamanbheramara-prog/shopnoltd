#!/usr/bin/env python3
"""Publish encrypted Shopnoltd backup artifacts through Git transport.

Large encrypted artifacts are written to a local clone and pushed with Git,
avoiding the Git Database API's JSON/base64 request-size limitation.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
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


def api(token: str, method: str, path: str) -> dict:
    request = urllib.request.Request(
        API + path,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Shopnoltd-Encrypted-Backup",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"GitHub API {method} {path} failed ({exc.code})."
        ) from None


def run(args: list[str], *, env: dict[str, str], cwd: pathlib.Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, env=env, check=True, stdin=subprocess.DEVNULL)


def main() -> int:
    repo = os.environ["BACKUP_REPOSITORY"]
    token = os.environ["BACKUP_REPOSITORY_TOKEN"]
    branch = os.environ.get("BACKUP_BRANCH", "database-backups")
    workdir = pathlib.Path(os.environ.get("BACKUP_WORKDIR", "/tmp/shopnoltd-dr-backup"))
    if not repo.count("/") == 1 or repo == os.environ.get("GITHUB_REPOSITORY"):
        raise SystemExit("Backup repository must be a separate owner/repository destination.")
    if not branch or branch.startswith("-") or any(c.isspace() for c in branch):
        raise SystemExit("Invalid backup branch name.")

    destination = api(token, "GET", f"/repos/{repo}")
    if destination.get("private") is not True:
        raise SystemExit("Refusing to publish: destination repository is not private.")

    for filename in FILES:
        path = workdir / filename
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"Required encrypted backup artifact is missing or empty: {filename}")
        if path.stat().st_size > 90 * 1024 * 1024:
            raise SystemExit(f"{filename} exceeds the safe GitHub file-size limit (90 MiB).")

    with tempfile.TemporaryDirectory(prefix="shopnoltd-backup-publish-") as temp:
        root = pathlib.Path(temp)
        clone = root / "backup-repo"
        askpass = root / "git-askpass.sh"
        askpass.write_text(
            '#!/bin/sh\ncase "$1" in\n'
            '  *Username*) printf "%s\\n" "x-access-token" ;;\n'
            '  *Password*) printf "%s\\n" "$BACKUP_REPOSITORY_TOKEN" ;;\n'
            '  *) exit 1 ;;\nesac\n',
            encoding="utf-8",
        )
        askpass.chmod(0o700)
        env = os.environ.copy()
        env.update({
            "GIT_ASKPASS": str(askpass),
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
        })
        remote = f"https://github.com/{repo}.git"

        # Fetch the existing backup branch if present; otherwise start at main.
        refs = api(token, "GET", f"/repos/{repo}/git/ref/heads/{branch}")
        if refs.get("object", {}).get("sha"):
            run(["git", "clone", "--quiet", "--single-branch", "--branch", branch, remote, str(clone)], env=env)
        else:
            run(["git", "clone", "--quiet", "--single-branch", "--branch", "main", remote, str(clone)], env=env)
            run(["git", "checkout", "-b", branch], env=env, cwd=clone)

        run(["git", "config", "user.name", "Shopnoltd Backup Automation"], env=env, cwd=clone)
        run(["git", "config", "user.email", "shopnoltd-backup[bot]@users.noreply.github.com"], env=env, cwd=clone)

        backup_dir = clone / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for filename in FILES:
            target = backup_dir / filename
            target.write_bytes((workdir / filename).read_bytes())
            target.chmod(0o600)
        (backup_dir / "README.md").write_text(README, encoding="utf-8")

        run(["git", "add", "--", "backup"], env=env, cwd=clone)
        changed = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=clone, env=env, check=False, stdin=subprocess.DEVNULL,
        ).returncode
        if changed == 0:
            print("PASS: encrypted backup artifacts already match the private backup branch.")
            return 0
        if changed != 1:
            raise RuntimeError("Unable to inspect staged backup changes.")

        run(
            ["git", "commit", "--quiet", "-m", "backup: encrypted PostgreSQL and Kubernetes Secrets snapshot"],
            env=env, cwd=clone,
        )
        # Normal fast-forward push only. Never force-update or rewrite backup history.
        run(["git", "push", "origin", f"HEAD:refs/heads/{branch}"], env=env, cwd=clone)

        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=clone, env=env,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        print(f"PASS: published {len(FILES)} encrypted backup artifacts to private repository {repo}.")
        print(f"PASS: branch {branch}, commit {head}; previous backup history preserved.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyError, OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
