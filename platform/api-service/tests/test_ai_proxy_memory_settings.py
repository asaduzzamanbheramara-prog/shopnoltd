from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.api import ai_proxy


def test_memory_settings_get_and_patch_use_explicit_proxy_route(monkeypatch):
    calls = []

    async def fake_proxy(request, upstream_path, token):
        calls.append((request.method, upstream_path, token))
        return Response(content='{"enabled":true}', media_type="application/json")

    monkeypatch.setattr(ai_proxy, "proxy", fake_proxy)
    app = FastAPI()
    app.include_router(ai_proxy.router)
    app.dependency_overrides[ai_proxy.raw_token] = lambda: "verified-user-token"

    with TestClient(app) as client:
        assert client.get("/ai/memories/settings").status_code == 200
        assert client.patch("/ai/memories/settings", json={"enabled": False}).status_code == 200

    assert calls == [
        ("GET", "/api/v1/memories/settings", "verified-user-token"),
        ("PATCH", "/api/v1/memories/settings", "verified-user-token"),
    ]
