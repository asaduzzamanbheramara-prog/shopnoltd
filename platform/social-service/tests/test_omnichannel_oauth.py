from app.api.omnichannel_oauth import _identity_fields


def test_tiktok_identity_uses_open_id_and_display_name():
    account_id, username, display_name = _identity_fields(
        "tiktok", {"open_id": "tt-user-123", "display_name": "Test Creator"}
    )
    assert account_id == "tt-user-123"
    assert username is None
    assert display_name == "Test Creator"


def test_instagram_identity_uses_professional_account_not_facebook_page():
    account_id, username, display_name = _identity_fields(
        "instagram",
        {"id": "ig-business-123", "username": "creator", "name": "Creator Page"},
    )
    assert account_id == "ig-business-123"
    assert username == "creator"
    assert display_name == "Creator Page"


def test_youtube_identity_uses_channel_id_not_google_subject():
    account_id, username, display_name = _identity_fields(
        "google", {"id": "UC-channel-123", "name": "Creator Channel"}, "youtube"
    )
    assert account_id == "UC-channel-123"
    assert display_name == "Creator Channel"


def test_tiktok_web_oauth_uses_comma_scopes_and_client_key_refresh():
    from app.api.omnichannel_oauth import _oauth_scope_string, _refresh_form

    assert _oauth_scope_string("tiktok", "tiktok") == "user.info.basic"
    form = _refresh_form(
        "tiktok",
        {"client_id": "tiktok-client-key", "client_secret": "secret"},
        "refresh-token",
        ["user.info.basic"],
    )
    assert form == {
        "grant_type": "refresh_token",
        "refresh_token": "refresh-token",
        "client_secret": "secret",
        "client_key": "tiktok-client-key",
    }


def test_scope_parser_accepts_provider_comma_and_space_formats():
    from app.api.omnichannel_oauth import _parse_scopes

    assert _parse_scopes("user.info.basic,video.list", []) == ["user.info.basic", "video.list"]
    assert _parse_scopes("openid profile email", []) == ["openid", "profile", "email"]
    assert _parse_scopes(None, ["fallback"]) == ["fallback"]


def test_tiktok_refresh_response_returns_rotated_refresh_expiry(monkeypatch):
    import asyncio
    from datetime import UTC, datetime
    from app.api import omnichannel_oauth as oauth

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 7200,
                "refresh_expires_in": 15552000,
                "scope": "user.info.basic",
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, data, headers):
            assert url == oauth.PROVIDER_CONFIG["tiktok"]["token_url"]
            assert data["client_key"] == "test-client-key"
            assert data["refresh_token"] == "old-refresh"
            return FakeResponse()

    monkeypatch.setitem(oauth.PROVIDER_CONFIG["tiktok"], "client_id", "test-client-key")
    monkeypatch.setitem(oauth.PROVIDER_CONFIG["tiktok"], "client_secret", "test-client-secret")
    monkeypatch.setattr(oauth.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    result = asyncio.run(
        oauth.refresh_provider_tokens("tiktok", "old-refresh", ["user.info.basic"])
    )
    assert result["access_token"] == "new-access"
    assert result["refresh_token"] == "new-refresh"
    assert result["scopes"] == ["user.info.basic"]
    assert result["expires_at"] > datetime.now(UTC)
    assert result["refresh_expires_at"] > datetime.now(UTC)


def test_oauth_start_route_requires_authenticated_post():
    from app.api.omnichannel_oauth import router

    route = next(
        route for route in router.routes
        if getattr(route, "path", "").endswith("/start/{provider}/{platform}")
    )
    assert route.methods == {"POST"}


def test_platform_identity_flows_request_only_required_scopes():
    from app.api.omnichannel_oauth import _scopes

    assert _scopes("tiktok", "tiktok") == ["user.info.basic"]
    instagram = _scopes("instagram", "instagram")
    assert "instagram_basic" in instagram
    assert "instagram_content_publish" not in instagram
    assert "instagram_manage_messages" not in instagram
    youtube = _scopes("google", "youtube")
    assert "https://www.googleapis.com/auth/youtube.readonly" in youtube
    assert "https://www.googleapis.com/auth/youtube" not in youtube
