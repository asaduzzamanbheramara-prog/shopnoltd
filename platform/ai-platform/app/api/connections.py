import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import current_user, require_admin, encrypt_secret, decrypt_secret, mask_secret
from app.db.models import AIConnection, GitHubWriteApproval
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/connections", tags=["connections"])


class ConnectionCreate(BaseModel):
    kind: str = Field(pattern="^(github|local)$")
    name: str = Field(min_length=1, max_length=120)
    base_url: str | None = None
    secret: str | None = None
    config: dict = Field(default_factory=dict)


class ConnectionUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    secret: str | None = None
    config: dict | None = None
    is_active: bool | None = None


def _out(c: AIConnection) -> dict:
    return {
        "id": str(c.id), "kind": c.kind, "name": c.name, "base_url": c.base_url,
        "config": c.config, "is_active": c.is_active,
        "secret_masked": mask_secret(decrypt_secret(c.secret_encrypted)) if c.secret_encrypted else "",
        "last_tested_at": c.last_tested_at, "last_test_status": c.last_test_status,
        "last_test_message": c.last_test_message,
    }


async def _owned(connection_id: uuid.UUID, user: dict, db: AsyncSession) -> AIConnection:
    c = (await db.execute(select(AIConnection).where(
        AIConnection.id == connection_id, AIConnection.user_id == str(user.get("sub"))
    ))).scalar_one_or_none()
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    return c


@router.get("")
async def list_connections(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIConnection).where(
        AIConnection.user_id == str(user.get("sub"))
    ).order_by(AIConnection.name.asc()))
    return [_out(c) for c in result.scalars().all()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_connection(body: ConnectionCreate, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    if body.kind == "github" and not body.secret:
        raise HTTPException(400, "GitHub access token is required")
    if body.kind == "local":
        if not body.base_url:
            raise HTTPException(400, "Local server base URL is required")
        parsed = urlparse(body.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(400, "Base URL must be an http(s) URL")
        if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            raise HTTPException(
                400,
                "Localhost points to the Shopnoltd AI pod, not your computer. "
                "Use a network-reachable local AI URL (for example your LAN host "
                "address or a secure tunnel URL).",
            )
    c = AIConnection(
        user_id=str(user.get("sub")), kind=body.kind, name=body.name.strip(),
        base_url=body.base_url.rstrip("/") if body.base_url else None,
        secret_encrypted=encrypt_secret(body.secret) if body.secret else None,
        config=body.config,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _out(c)


@router.patch("/{connection_id}")
async def update_connection(connection_id: uuid.UUID, body: ConnectionUpdate, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    c = await _owned(connection_id, user, db)
    if body.name is not None: c.name = body.name.strip()
    if body.base_url is not None: c.base_url = body.base_url.rstrip("/")
    if body.secret: c.secret_encrypted = encrypt_secret(body.secret)
    if body.config is not None: c.config = body.config
    if body.is_active is not None: c.is_active = body.is_active
    await db.commit()
    await db.refresh(c)
    return _out(c)


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(connection_id: uuid.UUID, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    c = await _owned(connection_id, user, db)
    await db.delete(c)
    await db.commit()


@router.post("/{connection_id}/test")
async def test_connection(connection_id: uuid.UUID, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    c = await _owned(connection_id, user, db)
    try:
        if c.kind == "github":
            token = decrypt_secret(c.secret_encrypted or "")
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get("https://api.github.com/user", headers={
                    "Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                })
                r.raise_for_status()
                data = r.json()
            msg = f"Connected as {data.get('login', 'GitHub user')}"
        else:
            headers = {}
            if c.secret_encrypted:
                headers["Authorization"] = f"Bearer {decrypt_secret(c.secret_encrypted)}"
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{c.base_url}/models", headers=headers)
                r.raise_for_status()
            msg = f"Local OpenAI-compatible server reachable ({r.status_code})"
        c.last_tested_at = datetime.now(timezone.utc)
        c.last_test_status = "ok"; c.last_test_message = msg
        await db.commit()
        return {"ok": True, "status": "ok", "message": msg}
    except Exception as exc:
        c.last_tested_at = datetime.now(timezone.utc)
        c.last_test_status = "error"; c.last_test_message = str(exc)[:1000]
        await db.commit()
        return {"ok": False, "status": "error", "message": str(exc)[:1000]}


@router.get("/{connection_id}/github/repos")
async def github_repos(connection_id: uuid.UUID, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    c = await _owned(connection_id, user, db)
    if c.kind != "github": raise HTTPException(400, "Not a GitHub connection")
    token = decrypt_secret(c.secret_encrypted or "")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get("https://api.github.com/user/repos?per_page=100&sort=updated",
            headers={"Accept":"application/vnd.github+json","Authorization":f"Bearer {token}","X-GitHub-Api-Version":"2022-11-28"})
        r.raise_for_status()
        return [{"full_name": x["full_name"], "default_branch": x.get("default_branch"), "private": x.get("private")} for x in r.json()]


@router.get("/{connection_id}/github/file")
async def github_file(connection_id: uuid.UUID, repo: str, path: str, ref: str | None = None, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    c = await _owned(connection_id, user, db)
    if c.kind != "github": raise HTTPException(400, "Not a GitHub connection")
    token = decrypt_secret(c.secret_encrypted or "")
    url = f"https://api.github.com/repos/{repo}/contents/{path.lstrip('/')}"
    params = {"ref": ref} if ref else {}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, params=params, headers={"Accept":"application/vnd.github.raw+json","Authorization":f"Bearer {token}","X-GitHub-Api-Version":"2022-11-28"})
        r.raise_for_status()
        return {"repo": repo, "path": path, "ref": ref, "content": r.text}


class GithubWriteOperation(BaseModel):
    repo: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=1_000_000)
    message: str = Field(min_length=1, max_length=200)
    branch: str = Field(min_length=1, max_length=255)
    sha: str | None = None


class GithubWriteApprovalRequest(GithubWriteOperation):
    """Submitting this endpoint is the explicit admin approval action."""


class GithubWrite(GithubWriteOperation):
    approval_id: uuid.UUID


def _github_write_digest(body: GithubWriteOperation) -> str:
    canonical = json.dumps(
        body.model_dump(mode="json", exclude={"approval_id"}), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@router.post("/{connection_id}/github/approvals", status_code=status.HTTP_201_CREATED)
async def approve_github_write(
    connection_id: uuid.UUID,
    body: GithubWriteApprovalRequest,
    user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a five-minute approval for this exact operation; approval is single-use."""
    c = await _owned(connection_id, user, db)
    if c.kind != "github":
        raise HTTPException(400, "Not a GitHub connection")
    if any(part == ".." for part in body.path.split("/")):
        raise HTTPException(400, "Invalid repository path")

    now = datetime.now(timezone.utc)
    approval = GitHubWriteApproval(
        connection_id=c.id,
        user_id=str(user.get("sub")),
        operation_hash=_github_write_digest(body),
        expires_at=now + timedelta(minutes=5),
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    return {
        "approval_id": str(approval.id),
        "expires_at": approval.expires_at,
        "single_use": True,
        "operation_sha256": approval.operation_hash,
    }


@router.put("/{connection_id}/github/file")
async def github_write_file(
    connection_id: uuid.UUID,
    body: GithubWrite,
    user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    c = await _owned(connection_id, user, db)
    if c.kind != "github":
        raise HTTPException(400, "Not a GitHub connection")

    now = datetime.now(timezone.utc)
    consumed = await db.execute(
        update(GitHubWriteApproval)
        .where(
            GitHubWriteApproval.id == body.approval_id,
            GitHubWriteApproval.connection_id == c.id,
            GitHubWriteApproval.user_id == str(user.get("sub")),
            GitHubWriteApproval.operation_hash == _github_write_digest(body),
            GitHubWriteApproval.expires_at > now,
            GitHubWriteApproval.consumed_at.is_(None),
        )
        .values(consumed_at=now)
        .returning(GitHubWriteApproval.id)
    )
    if consumed.scalar_one_or_none() is None:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Approval is missing, expired, already used, or does not match this exact operation",
        )
    # Consume before the external side effect. A failed GitHub call requires a fresh approval.
    await db.commit()

    token = decrypt_secret(c.secret_encrypted or "")
    import base64
    payload = {
        "message": body.message,
        "content": base64.b64encode(body.content.encode()).decode(),
        "branch": body.branch,
    }
    if body.sha:
        payload["sha"] = body.sha
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.put(
            f"https://api.github.com/repos/{body.repo}/contents/{body.path.lstrip('/')}",
            json=payload,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        r.raise_for_status()
        data = r.json()
    return {
        "ok": True,
        "commit": data.get("commit", {}).get("sha"),
        "content": data.get("content", {}).get("path"),
    }
