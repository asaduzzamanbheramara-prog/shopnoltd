"""Shopnoltd Mail Service."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from starlette.responses import Response

from app.core.config import settings
from app.core.db import Base, engine
from app.core.redis_client import redis_client

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await redis_client.ping()
    log.info("mail-service.started", env=settings.env)
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(title="Shopnoltd Mail Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    __import__("app.api.domains", fromlist=["router"]).router,
    prefix="/api/v1/domains",
    tags=["domains"],
)
app.include_router(
    __import__("app.api.mailboxes", fromlist=["router"]).router,
    prefix="/api/v1/mailboxes",
    tags=["mailboxes"],
)
app.include_router(
    __import__("app.api.messages", fromlist=["router"]).router,
    prefix="/api/v1/messages",
    tags=["messages"],
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
