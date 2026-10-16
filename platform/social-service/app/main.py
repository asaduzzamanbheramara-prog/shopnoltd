"""Shopnoltd Social Service."""

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from shopno_core.database.redis import redis_client
from shopno_core.database.dependencies import wait_for_dependencies
from starlette.responses import Response
from sqlalchemy import text

from app.core.config import settings
from app.core.db import Base, engine

log = structlog.get_logger()


async def _run_blog_scheduler() -> None:
    """Publish only explicitly scheduled blog posts once their UTC time arrives."""
    while True:
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text("""
                    UPDATE blog_posts
                    SET status='published', published_at=scheduled_at, updated_at=NOW()
                    WHERE status='scheduled' AND scheduled_at IS NOT NULL AND scheduled_at <= NOW()
                    RETURNING id
                """))
                published_ids = [str(row[0]) for row in result.fetchall()]
            if published_ids:
                log.info("blog.scheduled_posts_published", count=len(published_ids))
        except asyncio.CancelledError:
            raise
        except Exception:
            # Avoid logging SQL/connection details; retry on the next polling interval.
            log.error("blog.scheduled_publisher.poll_failed")
        await asyncio.sleep(15)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def _check_database():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    await wait_for_dependencies("social-service", _check_database, redis_client)
    blog_scheduler_task = asyncio.create_task(_run_blog_scheduler(), name="blog-scheduled-publisher")
    worker_task = None
    if settings.action_worker_enabled:
        from app.services.action_executor import run_action_worker
        worker_task = asyncio.create_task(run_action_worker(), name="social-action-worker")
        log.warning("social_action_worker.enabled", adapter_scope="telegram.send_message_only")
    log.info("social-service.started", env=settings.env)
    try:
        yield
    finally:
        blog_scheduler_task.cancel()
        try:
            await blog_scheduler_task
        except asyncio.CancelledError:
            pass
        if worker_task is not None:
            worker_task.cancel()
            try:
                await worker_task
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
app.include_router(__import__("app.api.shares", fromlist=["router"]).router, prefix="/api/v1/shares", tags=["shares"])
app.include_router(__import__("app.api.follows", fromlist=["router"]).router, prefix="/api/v1/follows", tags=["follows"])
app.include_router(__import__("app.api.post_views", fromlist=["router"]).router, prefix="/api/v1/views", tags=["views"])
app.include_router(__import__("app.api.reactions", fromlist=["router"]).router, prefix="/api/v1/reactions", tags=["reactions"])
app.include_router(__import__("app.api.omnichannel", fromlist=["router"]).router, prefix="/api/v1/omnichannel", tags=["omnichannel"])
app.include_router(__import__("app.api.omnichannel_oauth", fromlist=["router"]).router, prefix="/api/v1/omnichannel/oauth", tags=["omnichannel-oauth"])


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok", "social": True}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    async with engine.connect() as c:
        await c.execute(text("SELECT 1"))
    await redis_client.ping()
    return {"status": "ready", "social": True}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
