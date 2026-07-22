"""Shopnoltd OAuth Service."""

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
    log.info("oauth-service.started", env=settings.env)
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(title="Shopnoltd OAuth Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def _invalid_token(request, exc: ValueError):
    from starlette.responses import JSONResponse

    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(PermissionError)
async def _forbidden(request, exc: PermissionError):
    from starlette.responses import JSONResponse

    return JSONResponse(status_code=403, content={"detail": str(exc)})


app.include_router(
    __import__("app.api.users", fromlist=["router"]).router, prefix="/api/v1/users", tags=["users"]
)
app.include_router(
    __import__("app.api.tenants", fromlist=["router"]).router,
    prefix="/api/v1/tenants",
    tags=["tenants"],
)
app.include_router(
    __import__("app.api.roles", fromlist=["router"]).router, prefix="/api/v1/roles", tags=["roles"]
)
app.include_router(
    __import__("app.api.verify", fromlist=["router"]).router,
    prefix="/api/v1/verify",
    tags=["verify"],
)
app.include_router(
    __import__("app.api.customers", fromlist=["router"]).router,
    prefix="/api/v1/customers",
    tags=["customers"],
)
app.include_router(
    __import__("app.api.tenant_settings", fromlist=["router"]).router,
    prefix="/api/v1/tenants",
    tags=["tenant-settings"],
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
