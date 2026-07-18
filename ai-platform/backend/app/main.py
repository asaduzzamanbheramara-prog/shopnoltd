"""
Shopnoltd AI Platform — backend entrypoint.

Milestone 1 scope: FastAPI app, config, Docker, PostgreSQL, basic auth.
Later milestones (see README) add the AI engine, RAG, GitHub integration,
Kubernetes/Docker assistants, and the React frontend.
"""

from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_models
from app.routers import auth, chat, health
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before production use
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "milestone": 2, "status": "running"}
