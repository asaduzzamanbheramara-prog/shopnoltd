"""Guarded PostgreSQL backup/restore control plane.

This API orchestrates named backup/restore jobs; it never accepts arbitrary
shell commands, connection strings, paths, or SQL from callers. Production
execution is intentionally delegated to the deployment/operator layer.
"""
from datetime import datetime, timezone
import re

from app.api.admin import require_admin
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

_BACKUP_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")


class BackupRequest(BaseModel):
    backup_id: str = Field(min_length=3, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]{2,127}$")
    scope: str = Field(default="payment-service-postgres", pattern=r"^payment-service-postgres$")
    reason: str = Field(default="scheduled", max_length=500)


class RestoreRequest(BaseModel):
    backup_id: str = Field(min_length=3, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]{2,127}$")
    scope: str = Field(default="payment-service-postgres", pattern=r"^payment-service-postgres$")
    confirmation: str = Field(min_length=16, max_length=128)
    reason: str = Field(max_length=500)


def _platform_admin(user):
    if "platform_admin" not in set(user.get("roles", [])):
        raise HTTPException(403, "platform_admin required")


def _confirmation(backup_id: str) -> str:
    return f"RESTORE {backup_id}"


@router.get("/backups")
async def list_backups(user=Depends(require_admin)):
    _platform_admin(user)
    return {
        "scope": "payment-service-postgres",
        "status": "operator-managed",
        "backups": [],
        "message": "Backup inventory is supplied by the deployment/operator layer; no database filesystem is exposed through this API.",
    }


@router.post("/backups")
async def request_backup(req: BackupRequest, user=Depends(require_admin)):
    _platform_admin(user)
    if not _BACKUP_ID.fullmatch(req.backup_id):
        raise HTTPException(400, "invalid backup_id")
    return {
        "ok": True,
        "operation": "backup",
        "status": "requested",
        "backup_id": req.backup_id,
        "scope": req.scope,
        "reason": req.reason,
        "requested_by": user.get("sub"),
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "execution": "operator-managed",
        "safety": "No shell command, database credential, or filesystem path is accepted from the API.",
    }


@router.post("/backups/restore")
async def request_restore(req: RestoreRequest, user=Depends(require_admin)):
    _platform_admin(user)
    if req.confirmation != _confirmation(req.backup_id):
        raise HTTPException(400, f"restore requires confirmation exactly equal to '{_confirmation(req.backup_id)}'")
    return {
        "ok": True,
        "operation": "restore",
        "status": "approval-required",
        "backup_id": req.backup_id,
        "scope": req.scope,
        "reason": req.reason,
        "requested_by": user.get("sub"),
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "execution": "operator-managed",
        "safety": "Restore is not executed by the HTTP service; deployment automation must perform the privileged restore with a pre-restore backup and audit record.",
    }
