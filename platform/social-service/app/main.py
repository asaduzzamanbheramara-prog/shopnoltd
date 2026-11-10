"""Shopnoltd Social Service."""

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from shopno_core.database.dependencies import wait_for_dependencies
from shopno_core.database.redis import redis_client
from starlette.responses import Response

from app.core.config import settings
from app.core.db import Base, engine

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    executor_stop: asyncio.Event | None = None
    executor_task: asyncio.Task | None = None
    scheduler_stop: asyncio.Event | None = None
    scheduler_task: asyncio.Task | None = None

    async def _check_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    await wait_for_dependencies("social-service", _check_database, redis_client)
    from sqlalchemy import text
    async with engine.connect() as connection:
        scheduler_schema_ready = bool(await connection.scalar(text("""
            SELECT to_regclass('public.social_automation_schedules') IS NOT NULL
               AND to_regclass('public.social_post_drafts') IS NOT NULL
               AND to_regclass('public.omnichannel_oauth_tokens') IS NOT NULL
               AND to_regclass('public.platform_actions') IS NOT NULL
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='social_connections'
                     AND column_name='owner_user_id'
               )
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='social_automation_schedules'
                     AND column_name='paused_reason'
               )
               AND to_regclass('public.ux_social_automation_schedule_owner_slot') IS NOT NULL
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='omnichannel_oauth_tokens'
                     AND column_name='refresh_token_expires_at'
               )
        """)))
    if scheduler_schema_ready:
        from app.workers.social_scheduler import run_scheduler
        scheduler_stop = asyncio.Event()
        scheduler_task = asyncio.create_task(
            run_scheduler(scheduler_stop), name="social-approval-draft-scheduler"
        )
    else:
        log.warning("social-service.social_scheduler_schema_missing")
    if settings.omnichannel_executor_enabled and scheduler_schema_ready and settings.provider_oauth_encryption_ready:
        from app.workers.omnichannel_executor import run_executor
        executor_stop = asyncio.Event()
        executor_task = asyncio.create_task(run_executor(executor_stop), name="omnichannel-action-executor")
        log.warning("social-service.omnichannel_executor_enabled")
    elif not settings.omnichannel_executor_enabled:
        log.info("social-service.omnichannel_executor_disabled")
    elif not scheduler_schema_ready:
        log.warning("social-service.omnichannel_executor_schema_missing")
    else:
        log.warning("social-service.omnichannel_executor_encryption_key_missing")
    log.info("social-service.started", env=settings.env)
    try:
        yield
    finally:
        if scheduler_stop is not None:
            scheduler_stop.set()
        if scheduler_task is not None:
            try:
                await asyncio.wait_for(scheduler_task, timeout=30)
            except TimeoutError:
                scheduler_task.cancel()
                try:
                    await scheduler_task
                except asyncio.CancelledError:
                    pass
        if executor_stop is not None:
            executor_stop.set()
        if executor_task is not None:
            try:
                await asyncio.wait_for(executor_task, timeout=30)
            except TimeoutError:
                executor_task.cancel()
                try:
                    await executor_task
                except asyncio.CancelledError:
                    pass
        await engine.dispose()
        await redis_client.aclose()


app = FastAPI(title="Shopnoltd Social Service", version="0.6.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(__import__("app.api.posts", fromlist=["router"]).router, prefix="/api/v1/posts", tags=["posts"])
app.include_router(__import__("app.api.blog", fromlist=["router"]).router, prefix="/api/v1/blog", tags=["blog"])
app.include_router(__import__("app.api.admin_data", fromlist=["router"]).router, prefix="/api/v1/admin/blog-data", tags=["blog-admin-data"])
app.include_router(__import__("app.api.feed", fromlist=["router"]).router, prefix="/api/v1/feed", tags=["feed"])
app.include_router(__import__("app.api.likes", fromlist=["router"]).router, prefix="/api/v1/likes", tags=["likes"])
app.include_router(__import__("app.api.saved_posts", fromlist=["router"]).router, prefix="/api/v1/saved-posts", tags=["saved-posts"])
app.include_router(__import__("app.api.shares", fromlist=["router"]).router, prefix="/api/v1/shares", tags=["shares"])
app.include_router(__import__("app.api.follows", fromlist=["router"]).router, prefix="/api/v1/follows", tags=["follows"])
app.include_router(__import__("app.api.post_views", fromlist=["router"]).router, prefix="/api/v1/views", tags=["views"])
app.include_router(__import__("app.api.reactions", fromlist=["router"]).router, prefix="/api/v1/reactions", tags=["reactions"])
app.include_router(__import__("app.api.omnichannel", fromlist=["router"]).router, prefix="/api/v1/omnichannel", tags=["omnichannel"])
app.include_router(__import__("app.api.omnichannel_oauth", fromlist=["router"]).router, prefix="/api/v1/omnichannel/oauth", tags=["omnichannel-oauth"])
app.include_router(__import__("app.api.social_automation", fromlist=["router"]).router, prefix="/api/v1/omnichannel/automation", tags=["social-automation"])


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok", "social": True}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    from sqlalchemy import text

    async with engine.connect() as c:
        await c.execute(text("SELECT 1"))
    await redis_client.ping()
    return {"status": "ready", "social": True}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
