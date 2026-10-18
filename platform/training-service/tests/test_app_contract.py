"""Safe ASGI contract checks; deliberately bypass application lifespan and external services."""

import asyncio

import httpx
from app.main import app


def test_health_metrics_and_api_contract():
    async def check():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            health = await client.get("/healthz")
            assert health.status_code == 200
            assert health.json() == {"status": "ok"}

            metrics = await client.get("/metrics")
            assert metrics.status_code == 200
            assert "text/plain" in metrics.headers["content-type"]

            schema = await client.get("/openapi.json")
            assert schema.status_code == 200
            paths = schema.json()["paths"]
            for prefix in ["/api/v1/courses","/api/v1/lessons","/api/v1/enrollments","/api/v1/quizzes","/api/v1/certificates"]:
                assert any(path == prefix or path.startswith(prefix + "/") for path in paths), (
                    f"Expected API route prefix {prefix!r}; found {sorted(paths)}"
                )

    asyncio.run(check())
