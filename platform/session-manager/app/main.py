"""Shopnoltd Session Manager with fail-closed authentication for browser APIs."""
import os
from app.models.db import init_db
from app.routers import health, profiles, sessions
from app.services.session_pool import pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Shopnoltd Session Manager", description="Isolated browser-profile management for Shopnoltd.", version="0.2.0")

@app.on_event("startup")
def on_startup():
    init_db()

@app.on_event("shutdown")
async def on_shutdown():
    await pool.shutdown()

allowed_origins = [x.strip() for x in os.getenv("SESSION_MANAGER_ALLOWED_ORIGINS", "https://shopnoltd.dpdns.org,https://www.shopnoltd.dpdns.org").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])
app.include_router(health.router, tags=["health"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
# Proxy CRUD is withheld until proxy records have tenant ownership.
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
