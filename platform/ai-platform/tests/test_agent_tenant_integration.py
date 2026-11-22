import asyncio
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parents[2] / "shared" / "libraries" / "python"))

from app.api import agents
from app.core.security import current_user
from app.db.base import Base
from app.db.models import Agent, Conversation
from app.db.session import get_db


def test_agent_api_isolated_across_authenticated_tenants():
    async def scenario():
        database_url = os.environ["DATABASE_URL"]
        engine = create_async_engine(database_url, pool_pre_ping=True)
        sessions = async_sessionmaker(engine, expire_on_commit=False)

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

        claims = {"sub": "user-a", "tenant_id": "tenant-a"}
        app = FastAPI()
        app.include_router(agents.router, prefix="/agents")

        async def authenticated_user():
            return dict(claims)

        async def database_session():
            async with sessions() as session:
                yield session

        app.dependency_overrides[current_user] = authenticated_user
        app.dependency_overrides[get_db] = database_session

        fake_inference = types.ModuleType("app.api.inference")

        async def infer(payload, user):
            assert user["tenant_id"] == "tenant-a"
            return SimpleNamespace(response="safe test response")

        fake_inference.infer = infer
        original_inference = sys.modules.get("app.api.inference")
        sys.modules["app.api.inference"] = fake_inference

        try:
            transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                missing_tenant = {"sub": "user-x"}
                claims.clear()
                claims.update(missing_tenant)
                response = await client.post("/agents", json={"name": "blocked"})
                assert response.status_code == 403, response.text

                claims.clear()
                claims.update({"sub": "user-a", "tenant_id": "tenant-a"})
                created = await client.post("/agents", json={"name": "tenant-a agent"})
                assert created.status_code == 201, created.text
                agent_id = created.json()["id"]

                claims.clear()
                claims.update({"sub": "user-b", "tenant_id": "tenant-b"})
                other_tenant = await client.get("/agents")
                assert other_tenant.status_code == 200, other_tenant.text
                assert other_tenant.json() == []

                cross_tenant_chat = await client.post(
                    f"/agents/{agent_id}/chat", params={"message": "should not reach agent"}
                )
                assert cross_tenant_chat.status_code == 404, cross_tenant_chat.text

                claims.clear()
                claims.update({"sub": "user-a", "tenant_id": "tenant-a"})
                own_list = await client.get("/agents")
                assert own_list.status_code == 200, own_list.text
                assert [item["id"] for item in own_list.json()] == [agent_id]

                own_chat = await client.post(
                    f"/agents/{agent_id}/chat", params={"message": "hello"}
                )
                assert own_chat.status_code == 200, own_chat.text
                assert own_chat.json()["response"] == "safe test response"

            async with sessions() as session:
                stored = (await session.execute(
                    __import__("sqlalchemy").select(Conversation).where(
                        Conversation.agent_id == agent_id
                    )
                )).scalars().all()
                assert [(row.role, row.content) for row in stored] == [
                    ("user", "hello"),
                    ("assistant", "safe test response"),
                ]
        finally:
            if original_inference is None:
                sys.modules.pop("app.api.inference", None)
            else:
                sys.modules["app.api.inference"] = original_inference
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    asyncio.run(scenario())
