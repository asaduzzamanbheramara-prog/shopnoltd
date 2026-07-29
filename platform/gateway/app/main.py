"""Shopnoltd API Gateway."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from prometheus_client import generate_latest
from shopno_core.database.redis import redis_client
from sqlalchemy import text
from starlette.responses import Response

from app.core.config import settings
from app.core.db import Base, engine

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await redis_client.ping()

    log.info("gateway.started", env=settings.env)

    yield

    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(
    title="Shopnoltd API Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    __import__("app.api.routes", fromlist=["router"]).router,
    prefix="/api/routes",
    tags=["routes"],
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>Shopnoltd API Gateway</title>

<style>

body{
    margin:0;
    font-family:Arial,Helvetica,sans-serif;
    background:#f3f5f7;
}

header{
    background:#0057b8;
    color:white;
    padding:30px;
}

.container{
    max-width:1100px;
    margin:auto;
    padding:40px;
}

.card{
    background:white;
    border-radius:12px;
    padding:25px;
    margin-bottom:20px;
    box-shadow:0 3px 12px rgba(0,0,0,.08);
}

.grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
    gap:18px;
}

a{
    text-decoration:none;
    color:#0057b8;
    font-weight:bold;
}

.footer{
    color:#777;
    text-align:center;
    margin-top:40px;
}

</style>

</head>

<body>

<header>

<h1>🚀 Shopnoltd API Gateway</h1>

<p>Gateway is running successfully.</p>

</header>

<div class="container">

<div class="card">

<h2>System Status</h2>

<ul>
<li>Gateway: ✅ Running</li>
<li>FastAPI: ✅ Running</li>
<li>Database: ✅ Connected</li>
<li>Redis: ✅ Connected</li>
</ul>

</div>

<div class="grid">

<div class="card">
<h3>Swagger UI</h3>
<a href="/docs">Open Swagger</a>
</div>

<div class="card">
<h3>ReDoc</h3>
<a href="/redoc">Open ReDoc</a>
</div>

<div class="card">
<h3>OpenAPI</h3>
<a href="/openapi.json">Open JSON</a>
</div>

<div class="card">
<h3>Health</h3>
<a href="/healthz">Health Check</a>
</div>

<div class="card">
<h3>Ready</h3>
<a href="/readyz">Readiness Check</a>
</div>

<div class="card">
<h3>Metrics</h3>
<a href="/metrics">Prometheus Metrics</a>
</div>

</div>

<div class="footer">

<p>Shopnoltd Platform</p>

<p>API Gateway Version 0.1.0</p>

</div>

</div>

</body>

</html>
"""


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    await redis_client.ping()

    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(
        generate_latest(),
        media_type="text/plain; version=0.0.4",
    )
