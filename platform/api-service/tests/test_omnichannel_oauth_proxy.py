import asyncio

from fastapi.security import HTTPAuthorizationCredentials

from app.api import v1


def test_oauth_authorize_url_proxy_forwards_authenticated_user_token(monkeypatch):
    calls = {}

    async def fake_user_token(creds):
        assert creds.credentials == "user-jwt"
        return "verified-user-jwt"

    async def fake_call(method, url, token, **kwargs):
        calls.update(method=method, url=url, token=token, kwargs=kwargs)
        return {"authorization_url": "https://provider.example/authorize"}

    monkeypatch.setattr(v1, "omnichannel_user_token", fake_user_token)
    monkeypatch.setattr(v1, "call", fake_call)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="user-jwt")

    result = asyncio.run(v1.omnichannel_oauth_authorize_url("google", "gmail", creds))

    assert result == {"authorization_url": "https://provider.example/authorize"}
    assert calls == {
        "method": "GET",
        "url": f"{v1.SOCIAL}/api/v1/omnichannel/oauth/authorize-url/google/gmail",
        "token": "verified-user-jwt",
        "kwargs": {},
    }
