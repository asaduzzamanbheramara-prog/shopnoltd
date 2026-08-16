"""
Shopnoltd Session Manager
--------------------------
Isolated browser-session management for QA testing, staff tooling, and
scraping workflows. Each "profile" gets its own persistent browser context
(separate cookies, localStorage, cache) via Playwright — normal multi-tenant
session isolation, not fingerprint spoofing.
"""

from app.models.db import init_db
from app.routers import health, profiles, proxies, sessions
from app.services.session_pool import pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Shopnoltd Session Manager",
    description="Isolated browser-profile management for QA, staff tooling, and scraping.",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.on_event("shutdown")
async def on_shutdown():
    await pool.shutdown()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to shopnoltd.dpdns.org subdomains before prod
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(proxies.router, prefix="/api/proxies", tags=["proxies"])

app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
