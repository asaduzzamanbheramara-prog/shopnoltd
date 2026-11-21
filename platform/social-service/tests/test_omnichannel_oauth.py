from app.api.omnichannel_oauth import _identity_fields, _parse_scopes


def test_meta_comma_separated_permissions_are_parsed_individually():
    assert _parse_scopes("pages_show_list,instagram_basic", []) == [
        "pages_show_list", "instagram_basic"
    ]


def test_space_separated_oauth_scopes_are_parsed_individually():
    assert _parse_scopes("openid email profile", []) == ["openid", "email", "profile"]


def test_provider_scope_fallback_is_preserved_when_scope_is_omitted():
    assert _parse_scopes(None, ["user.info.basic"]) == ["user.info.basic"]


def test_instagram_identity_uses_professional_account_username():
    assert _identity_fields("instagram", {"id": "ig-1", "username": "shopno", "name": "Shopno"}) == (
        "ig-1", "shopno", "Shopno"
    )


def test_tiktok_identity_uses_open_id():
    assert _identity_fields("tiktok", {"open_id": "tt-1", "display_name": "Shopno"}) == (
        "tt-1", None, "Shopno"
    )


def test_youtube_identity_uses_channel_id_not_google_subject():
    assert _identity_fields("google", {"id": "channel-1", "username": "@shopno", "name": "Shopno Channel"}, "youtube") == (
        "channel-1", "@shopno", "Shopno Channel"
    )
from urllib.parse import parse_qs, urlparse

import app.api.omnichannel_oauth as oauth


def test_google_authorization_url_is_created_for_authenticated_user(monkeypatch):
    monkeypatch.setitem(oauth.PROVIDER_CONFIG, "google", {
        "platforms": ["gmail"],
        "client_id": "google-client-id",
        "client_secret": "server-only-secret",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["openid", "email"],
    })
    monkeypatch.setattr(oauth.settings, "provider_oauth_redirect_uri", "https://shopnoltd.example/callback")
    captured = {}
    monkeypatch.setattr(oauth, "_sign_state", lambda payload: captured.update(payload) or "signed-state")

    url = oauth._authorization_url("google", "gmail", {"sub": "user-1", "tenant_id": "tenant-1"})
    params = parse_qs(urlparse(url).query)

    assert params["client_id"] == ["google-client-id"]
    assert params["redirect_uri"] == ["https://shopnoltd.example/callback"]
    assert params["state"] == ["signed-state"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["access_type"] == ["offline"]
    assert captured["sub"] == "user-1"
    assert captured["tenant_id"] == "tenant-1"
    assert captured["provider"] == "google"
    assert captured["platform"] == "gmail"
    assert "server-only-secret" not in url


def test_meta_authorization_url_uses_state_without_pkce(monkeypatch):
    monkeypatch.setitem(oauth.PROVIDER_CONFIG, "facebook", {
        "platforms": ["facebook"],
        "client_id": "meta-client-id",
        "client_secret": "server-only-secret",
        "auth_url": "https://www.facebook.com/v24.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v24.0/oauth/access_token",
        "scopes": [],
    })
    monkeypatch.setattr(oauth.settings, "provider_oauth_redirect_uri", "https://shopnoltd.example/callback")
    monkeypatch.setattr(oauth, "_sign_state", lambda payload: "signed-meta-state")

    url = oauth._authorization_url("facebook", "facebook", {"sub": "user-1"})
    params = parse_qs(urlparse(url).query)

    assert params["client_id"] == ["meta-client-id"]
    assert params["state"] == ["signed-meta-state"]
    assert "code_challenge" not in params
    assert "server-only-secret" not in url


def test_multiple_provider_accounts_are_returned_for_explicit_selection():
    choices = [{"id": "page-1", "name": "Page One"}, {"id": "page-2", "name": "Page Two"}]
    assert oauth._account_choice(choices, "none") == {"_choices": choices}


def test_single_provider_account_connects_without_selection():
    choice = {"id": "page-1", "name": "Page One"}
    assert oauth._account_choice([choice], "none") == choice


def test_no_provider_accounts_fails_closed():
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc:
        oauth._account_choice([], "no eligible Page")
    assert exc.value.status_code == 409


def test_account_choice_discards_blank_and_duplicate_ids():
    choices = [
        {"id": "page-1", "name": "Page One"},
        {"id": "", "name": "Broken entry"},
        {"id": "page-1", "name": "Duplicate Page"},
    ]
    assert oauth._account_choice(choices, "none") == choices[0]


def test_meta_long_lived_exchange_uses_requested_provider_config(monkeypatch):
    monkeypatch.setitem(oauth.PROVIDER_CONFIG, "instagram", {
        "client_id": "instagram-app-id",
        "client_secret": "instagram-app-secret",
        "token_url": "https://graph.facebook.com/v24.0/oauth/access_token",
    })
    url, params = oauth._meta_token_exchange_request("instagram", "short-lived-token")
    assert url == "https://graph.facebook.com/v24.0/oauth/access_token"
    assert params["client_id"] == "instagram-app-id"
    assert params["client_secret"] == "instagram-app-secret"
    assert params["fb_exchange_token"] == "short-lived-token"


def test_youtube_requests_read_only_scope(monkeypatch):
    monkeypatch.setitem(oauth.PROVIDER_CONFIG, "google", {
        "platforms": ["youtube"],
        "client_id": "google-client-id",
        "client_secret": "google-client-secret",
        "scopes": ["openid", "email", "profile"],
    })
    assert "https://www.googleapis.com/auth/youtube.readonly" in oauth._scopes("google", "youtube")
    assert "https://www.googleapis.com/auth/youtube" not in oauth._scopes("google", "youtube")


def test_tiktok_web_authorization_uses_client_key_and_no_pkce(monkeypatch):
    monkeypatch.setitem(oauth.PROVIDER_CONFIG, "tiktok", {
        "platforms": ["tiktok"],
        "client_id": "tiktok-client-key",
        "client_secret": "server-only-secret",
        "auth_url": "https://www.tiktok.com/v2/auth/authorize/",
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
        "scopes": ["user.info.basic"],
    })
    monkeypatch.setattr(oauth.settings, "provider_oauth_redirect_uri", "https://shopnoltd.example/callback")
    monkeypatch.setattr(oauth, "_sign_state", lambda payload: "signed-tiktok-state")
    params = parse_qs(urlparse(oauth._authorization_url("tiktok", "tiktok", {"sub": "user-1"})).query)
    assert params["client_key"] == ["tiktok-client-key"]
    assert params["scope"] == ["user.info.basic"]
    assert params["state"] == ["signed-tiktok-state"]
    assert "client_id" not in params
    assert "code_challenge" not in params
    assert "server-only-secret" not in str(params)


def test_tiktok_token_exchange_unwraps_v2_data_and_checks_error_code(monkeypatch):
    import asyncio
    import pytest
    from fastapi import HTTPException

    class Response:
        status_code = 200
        def __init__(self, payload):
            self.payload = payload
        def json(self):
            return self.payload

    class Client:
        def __init__(self, payload):
            self.payload = payload
            self.request = None
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, url, **kwargs):
            self.request = (url, kwargs)
            return Response(self.payload)

    monkeypatch.setitem(oauth.PROVIDER_CONFIG, "tiktok", {
        "client_id": "client-key",
        "client_secret": "client-secret",
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
    })
    success = Client({"data": {"error_code": 0, "access_token": "access", "refresh_token": "refresh"}, "message": "success"})
    monkeypatch.setattr(oauth.httpx, "AsyncClient", lambda **kwargs: success)
    result = asyncio.run(oauth._exchange("tiktok", "auth-code", "unused-verifier"))
    assert result["access_token"] == "access"
    assert result["refresh_token"] == "refresh"
    assert success.request[1]["data"]["client_key"] == "client-key"
    assert success.request[1]["data"]["client_secret"] == "client-secret"

    rejected = Client({"data": {"error_code": 10001}, "message": "error"})
    monkeypatch.setattr(oauth.httpx, "AsyncClient", lambda **kwargs: rejected)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(oauth._exchange("tiktok", "bad-code", "unused-verifier"))
    assert exc.value.status_code == 400


def test_youtube_channel_discovery_follows_next_page_token(monkeypatch):
    import asyncio

    class Response:
        status_code = 200
        def __init__(self, payload):
            self.payload = payload
        def json(self):
            return self.payload

    class Client:
        def __init__(self):
            self.calls = []
            self.responses = [
                Response({"items": [{"id": "channel-1", "snippet": {"title": "First"}}], "nextPageToken": "page-2"}),
                Response({"items": [{"id": "channel-2", "snippet": {"title": "Second"}}]}),
            ]
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def get(self, url, **kwargs):
            self.calls.append(kwargs["params"].copy())
            return self.responses.pop(0)

    client = Client()
    monkeypatch.setattr(oauth.httpx, "AsyncClient", lambda **kwargs: client)
    result = asyncio.run(oauth._identity("google", "access-token", "youtube"))
    assert result["_choices"][0]["id"] == "channel-1"
    assert result["_choices"][1]["id"] == "channel-2"
    assert client.calls[0]["maxResults"] == 50
    assert client.calls[1]["pageToken"] == "page-2"


def test_meta_page_discovery_follows_after_cursor(monkeypatch):
    import asyncio

    class Response:
        status_code = 200
        def __init__(self, payload):
            self.payload = payload
        def json(self):
            return self.payload

    class Client:
        def __init__(self, responses):
            self.responses = list(responses)
            self.calls = []
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def get(self, url, **kwargs):
            self.calls.append(kwargs.get("params", {}).copy())
            return self.responses.pop(0)

    pages = Client([
        Response({"data": [{"id": "page-1", "name": "First", "access_token": "page-token-1"}],
                  "paging": {"cursors": {"after": "cursor-2"}}}),
        Response({"data": [{"id": "page-2", "name": "Second", "access_token": "page-token-2"}]}),
    ])
    permissions = Client([Response({"data": [{"permission": "pages_show_list", "status": "granted"}]})])
    clients = [pages, permissions]
    monkeypatch.setattr(oauth.httpx, "AsyncClient", lambda **kwargs: clients.pop(0))
    result = asyncio.run(oauth._identity("facebook", "user-token", "facebook"))
    assert [item["id"] for item in result["_choices"]] == ["page-1", "page-2"]
    assert pages.calls[0]["limit"] == 100
    assert pages.calls[1]["after"] == "cursor-2"
    assert result["_choices"][0]["_access_token"] == "page-token-1"
