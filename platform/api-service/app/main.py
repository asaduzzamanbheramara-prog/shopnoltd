"""Shopnoltd Unified API Service."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from shopno_core.database.redis import redis_client
from starlette.responses import Response

from app.core.config import settings
from app.core.db import Base, engine
from app.models.work import Work, WorkAssignment, WorkSubmission  # noqa: F401
from app.models.work_evidence import WorkTaskConfig, WorkSession, WorkEvidence, WorkEvent  # noqa: F401

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await redis_client.ping()
    log.info("api-service.started", env=settings.env)
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(title="Shopnoltd Unified API Service", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(__import__("app.api.v1", fromlist=["router"]).router, prefix="/api/v1", tags=["v1"])
app.include_router(__import__("app.api.admin_proxy", fromlist=["router"]).router, prefix="/api/v1", tags=["admin-data-facade"])
app.include_router(__import__("app.api.domain_proxy", fromlist=["router"]).router, prefix="/api/v1", tags=["domain-facade"])
app.include_router(__import__("app.api.v2", fromlist=["router"]).router, prefix="/api/v2", tags=["social-work"])
# Must precede the legacy blog facade because that facade also has /blog/{slug}.
app.include_router(__import__("app.api.v2_blog_user", fromlist=["router"]).router, prefix="/api/v2", tags=["blog-user"])
app.include_router(__import__("app.api.v2_blog", fromlist=["router"]).router, prefix="/api/v2", tags=["blog"])
app.include_router(__import__("app.api.v3_work", fromlist=["router"]).router, prefix="/api/v3", tags=["verified-work"])
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
