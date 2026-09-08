"""Shopnoltd Payment Service."""

import time
from contextlib import asynccontextmanager

import structlog
from app.api import admin, admin_tables, admin_reports, admin_backups, deposits, exchanges, methods, transactions, transfers, wallets, webhooks, withdrawals
from app.core.config import settings
from app.core.db import Base, engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from shopno_core.database.redis import redis_client
from sqlalchemy import text
from starlette.responses import Response

log = structlog.get_logger()
REQUESTS = Counter("shopno_payments_http_requests_total", "HTTP requests", ["method", "path", "code"])
LATENCY = Histogram("shopno_payments_http_latency_seconds", "HTTP latency", ["path"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS user_id VARCHAR(64)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_user_id ON transactions (user_id)"))
        await conn.execute(text("UPDATE transactions t SET user_id = w.user_id FROM wallets w WHERE t.wallet_id = w.id AND t.user_id IS NULL"))
    await redis_client.ping()
    log.info("payment-service.started", env=settings.env, version=settings.version)
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(title="Shopnoltd Payment Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origin_regex=r"https://([a-z0-9-]+\.)?shopnoltd\.dpdns\.org", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        log.exception("unhandled.error", path=request.url.path, err=str(exc))
        REQUESTS.labels(request.method, request.url.path, "500").inc()
        return JSONResponse({"detail": "Internal error"}, status_code=500)
    elapsed = time.perf_counter() - start
    LATENCY.labels(request.url.path).observe(elapsed)
    REQUESTS.labels(request.method, request.url.path, str(response.status_code)).inc()
    return response


app.include_router(wallets.router, prefix="/api/v1/wallets", tags=["wallets"])
app.include_router(deposits.router, prefix="/api/v1/deposits", tags=["deposits"])
app.include_router(withdrawals.router, prefix="/api/v1/withdrawals", tags=["withdrawals"])
app.include_router(transfers.router, prefix="/api/v1/transfers", tags=["transfers"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(exchanges.router, prefix="/api/v1/exchanges", tags=["exchanges"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(methods.router, prefix="/api/v1/methods", tags=["methods"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(admin_tables.router, prefix="/api/v1/admin", tags=["admin-tables"])
app.include_router(admin_reports.router, prefix="/api/v1/admin", tags=["admin-data-reports"])
app.include_router(admin_backups.router, prefix="/api/v1/admin", tags=["admin-backups"])


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    async with engine.connect() as c:
        await c.execute(text("SELECT 1"))
    await redis_client.ping()
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
