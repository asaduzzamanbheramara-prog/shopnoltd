import asyncio
import os
import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parents[1] / "shared" / "libraries" / "python"))

from app.api import conversations
from app.core.security import current_user
from app.db.base import Base
from app.db.session import get_db


def test_conversation_history_is_durable_and_isolated_by_tenant_and_user():
    async def scenario():
        engine = create_async_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

        claims = {"sub": "user-a", "tenant_id": "tenant-a"}
        app = FastAPI()
        app.include_router(conversations.router, prefix="/conversations")

        async def authenticated_user():
            return dict(claims)

        async def database_session():
            async with sessions() as session:
                yield session

        app.dependency_overrides[current_user] = authenticated_user
        app.dependency_overrides[get_db] = database_session

        try:
            transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                claims.clear()
                claims.update({"sub": "user-no-tenant"})
                denied = await client.get("/conversations")
                assert denied.status_code == 403

                claims.clear()
                claims.update({"sub": "user-a", "tenant_id": "tenant-a"})
                snapshot = {"chats": [{
                    "id": "chat-a", "title": "Durable thread", "model": "free-model",
                    "modelId": None, "messages": [
                        {"id": "m1", "role": "user", "content": "Hello"},
                        {"id": "m2", "role": "assistant", "content": "Welcome"},
                    ]
                }]}
                saved = await client.put("/conversations/sync", json=snapshot)
                assert saved.status_code == 200, saved.text
                assert saved.json()["saved"] == 1

                claims.clear()
                claims.update({"sub": "user-b", "tenant_id": "tenant-a"})
                other_user = await client.get("/conversations")
                assert other_user.status_code == 200
                assert other_user.json() == []

                claims.clear()
                claims.update({"sub": "user-c", "tenant_id": "tenant-b"})
                other_tenant = await client.get("/conversations")
                assert other_tenant.status_code == 200
                assert other_tenant.json() == []

                claims.clear()
                claims.update({"sub": "user-a", "tenant_id": "tenant-a"})
                restored = await client.get("/conversations")
                assert restored.status_code == 200
                assert restored.json()[0]["messages"] == snapshot["chats"][0]["messages"]

                claims.clear()
                claims.update({"sub": "user-b", "tenant_id": "tenant-a"})
                overwrite = await client.put("/conversations/sync", json=snapshot)
                assert overwrite.status_code == 404, overwrite.text

                claims.clear()
                claims.update({"sub": "user-a", "tenant_id": "tenant-a"})
                deleted = await client.delete("/conversations/chat-a")
                assert deleted.status_code == 204
                assert (await client.get("/conversations")).json() == []
        finally:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    asyncio.run(scenario())
