"""Shopnoltd AI Platform."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from shopno_core.database.redis import redis_client
from starlette.responses import Response

from app.core.config import settings
from app.core.db import Base, engine

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await redis_client.ping()
    log.info("ai-platform.started", env=settings.env)
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(title="Shopnoltd AI Platform", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    __import__("app.api.inference", fromlist=["router"]).router,
    prefix="/api/v1/inference",
    tags=["inference"],
)
app.include_router(
    __import__("app.api.embeddings", fromlist=["router"]).router,
    prefix="/api/v1/embeddings",
    tags=["embeddings"],
)
app.include_router(
    __import__("app.api.documents", fromlist=["router"]).router,
    prefix="/api/v1/documents",
    tags=["documents"],
)
app.include_router(
    __import__("app.api.agents", fromlist=["router"]).router,
    prefix="/api/v1/agents",
    tags=["agents"],
)


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
