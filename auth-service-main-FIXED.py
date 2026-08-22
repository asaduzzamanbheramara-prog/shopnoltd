"""Shopnoltd Auth Service."""

import asyncio
from contextlib import asynccontextmanager

import structlog
from app.core.config import settings
from app.core.db import Base, engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from shopno_core.database.redis import redis_client
from sqlalchemy.exc import OperationalError
from starlette.responses import Response

log = structlog.get_logger()

# Global state for database initialization
_db_initialized = False
_db_init_lock = asyncio.Lock()


async def _ensure_db_ready(max_retries: int = 30, retry_delay: int = 2):
    """Ensure database is ready with retries."""
    global _db_initialized

    if _db_initialized:
        return

    async with _db_init_lock:
        if _db_initialized:
            return

        for attempt in range(max_retries):
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                _db_initialized = True
                log.info("auth-service.db_initialized", attempt=attempt + 1)
                return
            except OperationalError as e:
                log.warning(
                    "auth-service.db_init_failed",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    log.error("auth-service.db_init_failed_final", error=str(e))
                    raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Non-blocking startup: initialize DB asynchronously without blocking app start
    try:
        await asyncio.wait_for(_ensure_db_ready(), timeout=60)
    except TimeoutError:
        log.warning("auth-service.db_init_timeout", timeout=60)
    except Exception as e:
        log.warning("auth-service.db_init_error", error=str(e))

    try:
        await asyncio.wait_for(redis_client.ping(), timeout=10)
    except TimeoutError:
        log.warning("auth-service.redis_timeout", timeout=10)
    except Exception as e:
        log.warning("auth-service.redis_error", error=str(e))

    log.info("auth-service.started", env=settings.env)
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(title="Shopnoltd Auth Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    __import__("app.api.auth", fromlist=["router"]).router, prefix="/api/v1/auth", tags=["auth"]
)
app.include_router(
    __import__("app.api.sessions", fromlist=["router"]).router,
    prefix="/api/v1/sessions",
    tags=["sessions"],
)


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    from sqlalchemy import text

    # Ensure DB is initialized before checking
    await _ensure_db_ready()

    try:
        async with engine.connect() as c:
            await c.execute(text("SELECT 1"))
    except Exception as e:
        log.warning("auth-service.readyz_db_check_failed", error=str(e))
        return {"status": "not_ready", "reason": "database"}, 503

    try:
        await redis_client.ping()
    except Exception as e:
        log.warning("auth-service.readyz_redis_check_failed", error=str(e))
        return {"status": "not_ready", "reason": "redis"}, 503

    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
