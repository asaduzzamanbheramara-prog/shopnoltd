import asyncio
import os
import sys
from pathlib import Path

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parents[1] / "shared" / "libraries" / "python"))

from app.api import memories
from app.core.security import current_user
from app.db.base import Base
from app.db.session import get_db


def test_personal_memory_crud_is_explicit_and_isolated_by_tenant_and_user():
    async def scenario():
        engine = create_async_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

        claims = {"sub": "user-a", "tenant_id": "tenant-a"}
        app = FastAPI()
        app.include_router(memories.router, prefix="/memories")

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
                assert (await client.get("/memories")).status_code == 403
                claims.clear()
                claims.update({"sub": "user-a", "tenant_id": "tenant-a"})
                created = await client.post("/memories", json={"category": "preferences", "content": "Use concise answers"})
                assert created.status_code == 201, created.text
                memory_id = created.json()["id"]
                assert created.json()["content"] == "Use concise answers"
                assert (await client.get("/memories")).json()[0]["id"] == memory_id

                claims.clear()
                claims.update({"sub": "user-b", "tenant_id": "tenant-a"})
                assert (await client.get("/memories")).json() == []
                assert (await client.patch(f"/memories/{memory_id}", json={"content": "tamper"})).status_code == 404
                assert (await client.delete(f"/memories/{memory_id}")).status_code == 204

                claims.clear()
                claims.update({"sub": "user-a", "tenant_id": "tenant-a"})
                still_owned = await client.get("/memories")
                assert still_owned.status_code == 200
                assert still_owned.json()[0]["content"] == "Use concise answers"
                updated = await client.patch(f"/memories/{memory_id}", json={"content": "Use Bangla explanations"})
                assert updated.status_code == 200, updated.text
                assert updated.json()["content"] == "Use Bangla explanations"
                deleted = await client.delete(f"/memories/{memory_id}")
                assert deleted.status_code == 204
                assert (await client.get("/memories")).json() == []
        finally:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    asyncio.run(scenario())
