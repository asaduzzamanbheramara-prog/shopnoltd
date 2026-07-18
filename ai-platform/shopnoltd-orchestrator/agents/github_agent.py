"""
Repo agent. Keeps a local checkout in sync and reports the commit SHA
used to tag images, so every build is traceable back to a commit.
"""

import subprocess

import config


def ensure_repo_current() -> str:
    """
    If GITHUB_REPO_URL is set, clone/pull it into config.REPO_ROOT.
    If not set, assume REPO_ROOT is already a working copy (e.g. your
    existing WSL checkout) and just read its current commit.
    Returns the short commit SHA.
    """
    root = config.REPO_ROOT
    if config.GITHUB_REPO_URL:
        if not (root / ".git").exists():
            root.parent.mkdir(parents=True, exist_ok=True)
            auth_url = _inject_token(config.GITHUB_REPO_URL, config.GITHUB_TOKEN)
            subprocess.run(["git", "clone", auth_url, str(root)], check=True)
        else:
            subprocess.run(["git", "-C", str(root), "fetch", "--all"], check=True)
            subprocess.run(["git", "-C", str(root), "pull", "--ff-only"], check=True)

    sha = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return sha


def _inject_token(url: str, token: str) -> str:
    if token and url.startswith("https://"):
        return url.replace("https://", f"https://{token}@", 1)
    return url


def find_missing_dockerfiles(service_configs) -> list:
    """Sanity check: flag services whose declared Dockerfile doesn't exist."""
    missing = []
    for svc in service_configs:
        path = config.REPO_ROOT / svc.dockerfile
        if not path.exists():
            missing.append(svc.name)
    return missing
