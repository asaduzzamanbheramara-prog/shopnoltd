import pytest

from app.core import security


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"keys": [{"kid": "test-key"}]}


class FakeClient:
    requested_url = None

    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        type(self).requested_url = url
        return FakeResponse()


@pytest.mark.asyncio
async def test_jwks_uses_configured_internal_endpoint(monkeypatch):
    expected = (
        "http://keycloak.shopno-identity.svc.cluster.local/"
        "realms/shopnoltd/protocol/openid-connect/certs"
    )
    monkeypatch.setattr(security.settings, "keycloak_jwks_url", expected)
    monkeypatch.setattr(security.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(security, "_jwks_cache", None)

    result = await security._jwks()

    assert result == {"keys": [{"kid": "test-key"}]}
    assert FakeClient.requested_url == expected
    assert security.settings.keycloak_issuer == "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
