"""Shopnoltd Unified API Service."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from shopno_core.database.redis import redis_client
from shopno_core.database.dependencies import wait_for_dependencies
from sqlalchemy import text
from starlette.responses import Response

from app.core.config import settings
from app.core.db import Base, engine
from app.models.work import Work, WorkAssignment, WorkSubmission  # noqa: F401
from app.models.work_evidence import WorkTaskConfig, WorkSession, WorkEvidence, WorkEvent, GlobalTaskRate
from app.models.work_rating import WorkRating  # noqa: F401
from app.models.referral import ReferralCode, Referral, ReferralPolicy, ReferralReward, ReferralSystemIdentity  # noqa: F401

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def _check_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Idempotent compatibility migration for the reference image added to works.
            # Keep this DDL static; it is safe to run on every startup and upgrades
            # existing databases where create_all cannot add a missing column.
            await conn.execute(text("ALTER TABLE works ADD COLUMN IF NOT EXISTS reference_image TEXT"))
            await conn.execute(text("ALTER TABLE works ADD COLUMN IF NOT EXISTS before_post_screenshot TEXT"))
            await conn.execute(text("ALTER TABLE works ADD COLUMN IF NOT EXISTS task_type VARCHAR(32) NOT NULL DEFAULT 'simple'"))
            await conn.execute(text("ALTER TABLE works ADD COLUMN IF NOT EXISTS platform VARCHAR(64) NOT NULL DEFAULT 'shopnoltd'"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_works_task_type ON works (task_type)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_works_platform ON works (platform)"))
            # Referral compatibility columns preserve existing direct/legacy mappings.
            await conn.execute(text("ALTER TABLE referrals ADD COLUMN IF NOT EXISTS source VARCHAR(24) NOT NULL DEFAULT 'direct'"))
            await conn.execute(text("ALTER TABLE referral_policies ADD COLUMN IF NOT EXISTS fallback_referrer_id VARCHAR(128) NOT NULL DEFAULT 'admin_office'"))
            await conn.execute(text("UPDATE referral_policies SET fallback_referrer_id = 'admin_office' WHERE fallback_referrer_id IS NULL OR fallback_referrer_id = ''"))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS referral_system_identities (
                    alias VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(128) NOT NULL UNIQUE,
                    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_referral_system_identities_user_id ON referral_system_identities (user_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_referral_system_identities_tenant_id ON referral_system_identities (tenant_id)"))
            # Some recovered deployments keep identity users in Keycloak rather than
            # a legacy public.users table. Only seed the legacy mapping when that
            # table actually exists; its absence must not prevent API startup.
            await conn.execute(text("""
                DO $$
                BEGIN
                    IF to_regclass('public.users') IS NOT NULL THEN
                        INSERT INTO referral_system_identities (alias, user_id, tenant_id, active)
                        SELECT 'admin_office', id, 'default', 1
                        FROM users WHERE lower(email) = 'admin@shopnoltd.kesug.com'
                        ORDER BY id LIMIT 1
                        ON CONFLICT (alias) DO UPDATE SET user_id=EXCLUDED.user_id, tenant_id=EXCLUDED.tenant_id, active=1, updated_at=CURRENT_TIMESTAMP;
                    END IF;
                END $$;
            """))
            # Global task rates are keyed by task type + currency. This compatibility
            # migration upgrades databases created by the earlier single-currency model.
            await conn.execute(text("ALTER TABLE global_task_rates ADD COLUMN IF NOT EXISTS platform VARCHAR(64) NOT NULL DEFAULT 'shopnoltd'"))
            await conn.execute(text("ALTER TABLE global_task_rates ADD COLUMN IF NOT EXISTS currency VARCHAR(16) NOT NULL DEFAULT 'USD'"))
            await conn.execute(text("ALTER TABLE global_task_rates DROP CONSTRAINT IF EXISTS global_task_rates_pkey"))
            await conn.execute(text("ALTER TABLE global_task_rates ADD PRIMARY KEY (platform, task_type, currency)"))
    await wait_for_dependencies("api-service", _check_database, redis_client)
    log.info("api-service.started", env=settings.env)
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(title="Shopnoltd Unified API Service", version="0.4.2", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origin_regex=settings.cors_origin_regex, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(__import__("app.api.analytics_proxy", fromlist=["router"]).router, prefix="/api/v1", tags=["analytics"])
app.include_router(__import__("app.api.ad_proxy", fromlist=["router"]).router, prefix="/api/v1", tags=["advertising"])
app.include_router(__import__("app.api.v1", fromlist=["router"]).router, prefix="/api/v1", tags=["v1"])
app.include_router(__import__("app.api.direct_payment_proxy", fromlist=["router"]).router, prefix="/api/v1", tags=["direct-payments"])
app.include_router(__import__("app.api.payment_account_proxy", fromlist=["router"]).router, prefix="/api/v1", tags=["payment-accounts"])
app.include_router(__import__("app.api.admin_proxy", fromlist=["router"]).router, prefix="/api/v1", tags=["admin-data-facade"])
app.include_router(__import__("app.api.database_control_plane", fromlist=["router"]).router, prefix="/api/v1", tags=["admin-database-control-plane"])
app.include_router(__import__("app.api.database_control", fromlist=["router"]).router, prefix="/api/v1", tags=["admin-database"])
app.include_router(__import__("app.api.domain_proxy", fromlist=["router"]).router, prefix="/api/v1", tags=["domain-facade"])
app.include_router(__import__("app.api.freedomain_proxy", fromlist=["router"]).router, prefix="/api/v1", tags=["free-domain-facade"])
app.include_router(__import__("app.api.ai_proxy", fromlist=["router"]).router, prefix="/api/v1", tags=["ai-facade"])
app.include_router(__import__("app.api.storage_proxy", fromlist=["router"]).router, prefix="/api/v1", tags=["storage-facade"])
app.include_router(__import__("app.api.v2", fromlist=["router"]).router, prefix="/api/v2", tags=["social-work"])
app.include_router(__import__("app.api.v2_blog_user", fromlist=["router"]).router, prefix="/api/v2", tags=["blog-user"])
app.include_router(__import__("app.api.v2_blog", fromlist=["router"]).router, prefix="/api/v2", tags=["blog"])
app.include_router(__import__("app.api.v3_work", fromlist=["router"]).router, prefix="/api/v3", tags=["verified-work"])
app.include_router(__import__("app.api.referrals", fromlist=["router"]).router, prefix="/api/v1", tags=["referrals"])
app.include_router(__import__("app.api.graphql", fromlist=["router"]).router, prefix="/graphql", tags=["graphql"])
app.include_router(__import__("app.api.health", fromlist=["router"]).router, prefix="", tags=["health"])


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    from sqlalchemy import text
    async with engine.connect() as c:
        await c.execute(text("SELECT 1"))
    await redis_client.ping()
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
