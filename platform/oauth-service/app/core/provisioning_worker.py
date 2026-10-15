"""Bounded background reconciliation for durable account provisioning jobs.

Mailbox jobs are intentionally not processed here until mailbox activation/reset is
implemented. They remain pending rather than creating an inaccessible mailbox or
claiming that provisioning succeeded.
"""
import asyncio
from datetime import datetime, timedelta

import httpx
import structlog
from sqlalchemy import or_, select

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.models import AccountProvisioningJob, UserMirror

log = structlog.get_logger()
POLL_SECONDS = 10
MAX_ATTEMPTS = 8
LEASE_MINUTES = 5


def domain_confirmation_is_valid(body: object) -> bool:
    """Require an explicit active status and a non-empty domain before acknowledging work."""
    return isinstance(body, dict) and body.get("status") == "active" and isinstance(body.get("subdomain"), str) and bool(body["subdomain"].strip())


async def process_one_subdomain_job() -> bool:
    """Claim one job with SKIP LOCKED, then call the idempotent domain endpoint."""
    now = datetime.utcnow()
    async with SessionLocal() as session:
        async with session.begin():
            job = (
                await session.execute(
                    select(AccountProvisioningJob)
                    .where(
                        AccountProvisioningJob.resource_type == "subdomain",
                        or_(
                            (AccountProvisioningJob.attempts < MAX_ATTEMPTS)
                            & AccountProvisioningJob.status.in_(("pending", "failed")),
                            (AccountProvisioningJob.status == "processing")
                            & (AccountProvisioningJob.updated_at < now - timedelta(minutes=LEASE_MINUTES)),
                        ),
                    )
                    .order_by(AccountProvisioningJob.created_at, AccountProvisioningJob.id)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if job is None:
                return False
            if job.status == "processing" and job.attempts >= MAX_ATTEMPTS:
                job.status = "failed"
                job.last_error = "retry_limit_exhausted"
                job.updated_at = now
                return True
            user = (
                await session.execute(
                    select(UserMirror).where(UserMirror.id == job.user_id)
                )
            ).scalar_one_or_none()
            if user is None or not user.active or user.keycloak_id != job.keycloak_id:
                job.status = "failed"
                job.attempts = MAX_ATTEMPTS
                job.last_error = "identity_missing_or_inactive"
                job.updated_at = now
                return True
            job.status = "processing"
            job.attempts += 1
            job.last_error = None
            job.updated_at = now
            job_id = job.id
            keycloak_id = job.keycloak_id
            username = (user.email or "").split("@", 1)[0].strip()
            attempt = job.attempts

    # Do not hold a database lock during network I/O.
    try:
        if not settings.account_provisioning_internal_key:
            raise RuntimeError("internal_auth_not_configured")
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=4.0)) as client:
            response = await client.post(
                f"{settings.freedomain_service_url.rstrip('/')}/api/v1/domains/internal/provision",
                json={"keycloak_id": keycloak_id, "username": username},
                headers={"X-Account-Provisioning-Key": settings.account_provisioning_internal_key},
            )
            response.raise_for_status()
            body = response.json()
            if not domain_confirmation_is_valid(body):
                raise RuntimeError("provider_confirmation_missing")
    except Exception as exc:
        # Store only a fixed error code, never response bodies, URLs with credentials,
        # exception text, or secrets.
        error_code = "internal_auth_not_configured" if str(exc) == "internal_auth_not_configured" else "domain_provider_unavailable"
        async with SessionLocal() as session:
            async with session.begin():
                job = await session.get(AccountProvisioningJob, job_id, with_for_update=True)
                if job is not None and job.status == "processing":
                    job.status = "failed" if job.attempts >= MAX_ATTEMPTS else "pending"
                    job.last_error = error_code
                    job.updated_at = datetime.utcnow()
        log.warning("account_provisioning.domain_attempt_failed", job_id=job_id, attempt=attempt, reason=error_code)
        return True

    async with SessionLocal() as session:
        async with session.begin():
            job = await session.get(AccountProvisioningJob, job_id, with_for_update=True)
            if job is not None and job.status == "processing":
                job.status = "active"
                job.last_error = None
                job.updated_at = datetime.utcnow()
    log.info("account_provisioning.domain_active", job_id=job_id, attempt=attempt)
    return True


async def provisioning_worker() -> None:
    """Poll continuously; disabled by default until Kubernetes secrets are configured."""
    if not settings.account_provisioning_worker_enabled:
        log.info("account_provisioning.worker_disabled")
        return
    while True:
        try:
            processed = await process_one_subdomain_job()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("account_provisioning.worker_iteration_failed")
            processed = False
        if not processed:
            await asyncio.sleep(POLL_SECONDS)
