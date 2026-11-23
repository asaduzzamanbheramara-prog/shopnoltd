import asyncio

from app.core import security


def test_ai_platform_accepts_api_service_forwarded_tokens_with_strict_issuer(monkeypatch):
    captured = {}

    monkeypatch.setattr(security.jwt, "get_unverified_header", lambda token: {"kid": "test-key"})

    async def fake_jwks():
        return {"keys": [{"kid": "test-key", "alg": "RS256"}]}

    def fake_decode(token, key, **kwargs):
        captured.update(kwargs)
        return {"sub": "user-1", "tenant_id": "tenant-1"}

    monkeypatch.setattr(security, "_jwks", fake_jwks)
    monkeypatch.setattr(security.jwt, "decode", fake_decode)

    claims = asyncio.run(security.verify_token("test-token"))

    assert claims["sub"] == "user-1"
    assert set(captured["audience"]) == {"ai-platform", "api-service"}
    assert captured["issuer"] == security.settings.keycloak_issuer
    assert captured["options"] == {"verify_aud": True, "verify_iss": True}
