"""Shopnoltd Social Service."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from starlette.responses import Response
import structlog
from app.core.config import settings
from app.core.db import engine, Base
from app.core.redis_client import redis_client

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await redis_client.ping()
    log.info("social-service.started", env=settings.env)
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(title="Shopnoltd Social Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(__import__("app.api.posts", fromlist=["router"]).router, prefix="/api/v1/posts", tags=["posts"])
app.include_router(__import__("app.api.feed", fromlist=["router"]).router, prefix="/api/v1/feed", tags=["feed"])
app.include_router(__import__("app.api.likes", fromlist=["router"]).router, prefix="/api/v1/likes", tags=["likes"])
app.include_router(__import__("app.api.shares", fromlist=["router"]).router, prefix="/api/v1/shares", tags=["shares"])
app.include_router(__import__("app.api.follows", fromlist=["router"]).router, prefix="/api/v1/follows", tags=["follows"])



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
