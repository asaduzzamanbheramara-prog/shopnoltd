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
    assert params["prompt"] == ["consent select_account"]
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


def test_telegram_readiness_uses_bot_token_not_oauth_client_secret(monkeypatch):
    from app.api.omnichannel import PROVIDER_CONFIG

    monkeypatch.setitem(PROVIDER_CONFIG, "telegram", {
        "platforms": ["telegram"], "mode": "bot", "bot_token": "server-side-bot-token",
        "credential_keys": ["TELEGRAM_BOT_TOKEN"],
    })
    cfg = PROVIDER_CONFIG["telegram"]
    assert bool(cfg.get("bot_token")) is True
    assert not cfg.get("auth_url")


def test_whatsapp_readiness_requires_separate_business_onboarding(monkeypatch):
    from app.api.omnichannel import PROVIDER_CONFIG

    monkeypatch.setitem(PROVIDER_CONFIG, "whatsapp", {
        "platforms": ["whatsapp"], "mode": "business_cloud",
        "client_id": "meta-app-id", "client_secret": "server-side-secret",
        "setup_status": "business_onboarding_required",
    })
    cfg = PROVIDER_CONFIG["whatsapp"]
    assert bool(cfg.get("client_id") and cfg.get("client_secret")) is True
    assert cfg["setup_status"] == "business_onboarding_required"


def test_3cx_readiness_requires_api_base_url(monkeypatch):
    from app.api.omnichannel import PROVIDER_CONFIG

    monkeypatch.setitem(PROVIDER_CONFIG, "3cx", {
        "platforms": ["3cx"], "mode": "provider_api",
        "client_id": "client-id", "client_secret": "server-side-secret",
        "base_url": None,
    })
    cfg = PROVIDER_CONFIG["3cx"]
    assert not bool(cfg.get("client_id") and cfg.get("client_secret") and cfg.get("base_url"))


def test_provider_status_reports_mode_specific_readiness(monkeypatch):
    import asyncio
    from app.api import omnichannel

    monkeypatch.setattr(omnichannel, "PROVIDER_CONFIG", {
        "google": {
            "platforms": ["gmail", "youtube"], "client_id": "id", "client_secret": "secret",
            "auth_url": "https://accounts.example/auth", "token_url": "https://accounts.example/token",
            "credential_keys": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"], "mode": "oauth2",
        },
        "telegram": {
            "platforms": ["telegram"], "bot_token": "bot-token", "mode": "bot",
            "credential_keys": ["TELEGRAM_BOT_TOKEN"],
        },
        "whatsapp": {
            "platforms": ["whatsapp"], "client_id": "app-id", "client_secret": "app-secret",
            "mode": "business_cloud", "setup_status": "business_onboarding_required",
            "credential_keys": ["WHATSAPP_CLIENT_ID", "WHATSAPP_CLIENT_SECRET"],
        },
        "3cx": {
            "platforms": ["3cx"], "client_id": "id", "client_secret": "secret",
            "base_url": None, "mode": "provider_api",
            "credential_keys": ["THREECX_CLIENT_ID", "THREECX_CLIENT_SECRET", "THREECX_BASE_URL"],
        },
    })

    statuses = asyncio.run(omnichannel.provider_status(user={"sub": "user-1"}))
    by_provider = {item["provider"]: item for item in statuses}

    assert by_provider["google"]["configured"] is True
    assert by_provider["google"]["setup_status"] == "ready_to_authorize"
    assert by_provider["telegram"]["configured"] is True
    assert by_provider["telegram"]["setup_status"] == "bot_configured"
    assert by_provider["whatsapp"]["configured"] is True
    assert by_provider["whatsapp"]["setup_status"] == "business_onboarding_required"
    assert by_provider["3cx"]["configured"] is False
    assert by_provider["3cx"]["setup_status"] == "needs_api_credentials_and_base_url"
    assert "app-secret" not in str(statuses)


def test_connection_listing_is_scoped_to_authenticated_user():
    import asyncio
    from app.api.omnichannel import list_connections

    class Result:
        def mappings(self):
            return self
        def all(self):
            return []

    class Session:
        query = None
        params = None
        async def execute(self, query, params):
            self.query, self.params = str(query), params
            return Result()

    session = Session()
    asyncio.run(list_connections(
        user={"sub": "user-A", "tenant_id": "tenant-1"}, s=session
    ))
    assert "owner_user_id=:user" in session.query
    assert session.params == {"tenant": "tenant-1", "user": "user-A"}


def test_connection_detail_is_scoped_to_authenticated_user():
    import asyncio
    from app.api.omnichannel import get_connection

    class Result:
        def __init__(self, row):
            self.row = row
        def mappings(self):
            return self
        def one_or_none(self):
            return self.row
        def all(self):
            return []

    class Session:
        def __init__(self):
            self.calls = []
        async def execute(self, query, params):
            self.calls.append((str(query), params))
            if len(self.calls) == 1:
                return Result({"id": "connection-1", "platform": "facebook"})
            return Result([])

    session = Session()
    asyncio.run(get_connection(
        "connection-1", user={"sub": "user-A", "tenant_id": "tenant-1"}, s=session
    ))
    assert "owner_user_id=:user" in session.calls[0][0]
    assert session.calls[0][1] == {
        "tenant": "tenant-1", "user": "user-A", "id": "connection-1"
    }


def test_connection_update_is_scoped_to_authenticated_user():
    import asyncio
    from app.api.omnichannel import ConnectionPatch, update_connection

    class Result:
        def mappings(self):
            return self
        def one_or_none(self):
            return {"id": "connection-1"}

    class Session:
        query = None
        params = None
        async def execute(self, query, params):
            self.query, self.params = str(query), params
            return Result()
        async def commit(self):
            pass

    session = Session()
    asyncio.run(update_connection(
        "connection-1", ConnectionPatch(display_name="My Page"),
        user={"sub": "user-A", "tenant_id": "tenant-1"}, s=session
    ))
    assert "owner_user_id=:user" in session.query
    assert session.params["user"] == "user-A"


def test_multiple_selected_provider_profiles_are_deduplicated():
    assert oauth._selected_account_ids({"account_ids": ["page-1", "page-2", "page-1"]}) == [
        "page-1", "page-2"
    ]


def test_legacy_single_account_selection_remains_supported():
    assert oauth._selected_account_ids({"account_id": "page-1"}) == ["page-1"]


def test_empty_multi_profile_selection_is_rejected():
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc:
        oauth._selected_account_ids({"account_ids": []})
    assert exc.value.status_code == 422


def test_unknown_or_blank_selection_values_are_not_accepted_as_selection():
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc:
        oauth._selected_account_ids({"account_ids": [" ", None]})
    assert exc.value.status_code == 422


def test_multi_profile_selection_is_bounded():
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc:
        oauth._selected_account_ids({"account_ids": [f"profile-{i}" for i in range(101)]})
    assert exc.value.status_code == 422


def test_microsoft_authorization_url_prompts_for_account_selection(monkeypatch):
    monkeypatch.setitem(oauth.PROVIDER_CONFIG, "microsoft", {
        "platforms": ["outlook"],
        "client_id": "microsoft-client-id",
        "client_secret": "server-only-secret",
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": ["openid", "profile", "offline_access"],
    })
    monkeypatch.setattr(oauth.settings, "provider_oauth_redirect_uri", "https://shopnoltd.example/callback")
    monkeypatch.setattr(oauth, "_sign_state", lambda payload: "signed-ms-state")

    url = oauth._authorization_url("microsoft", "outlook", {"sub": "user-1"})
    params = parse_qs(urlparse(url).query)

    assert params["prompt"] == ["select_account"]
    assert params["client_id"] == ["microsoft-client-id"]
    assert "server-only-secret" not in url



def test_manual_connection_defaults_to_pending_and_cannot_claim_connected():
    import pytest
    from pydantic import ValidationError
    from app.api.omnichannel import ConnectionIn

    connection = ConnectionIn(platform="facebook", platform_account_id="page-1")
    assert connection.status == "pending"

    with pytest.raises(ValidationError):
        ConnectionIn(platform="facebook", platform_account_id="page-1", status="connected")


def test_manual_connection_patch_cannot_mark_profile_connected():
    import pytest
    from pydantic import ValidationError
    from app.api.omnichannel import ConnectionPatch

    with pytest.raises(ValidationError):
        ConnectionPatch(status="connected")

    assert ConnectionPatch(status="pending").status == "pending"



def test_github_authorization_url_uses_pkce_and_offline_access(monkeypatch):
    monkeypatch.setitem(oauth.PROVIDER_CONFIG, "github", {
        "platforms": ["github"],
        "client_id": "github-client-id",
        "client_secret": "server-only-secret",
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "scopes": ["read:user", "user:email", "offline_access"],
    })
    monkeypatch.setattr(oauth.settings, "provider_oauth_redirect_uri", "https://shopnoltd.example/callback")
    monkeypatch.setattr(oauth, "_sign_state", lambda payload: "signed-github-state")

    url = oauth._authorization_url("github", "github", {"sub": "user-1"})
    params = parse_qs(urlparse(url).query)

    assert params["client_id"] == ["github-client-id"]
    assert params["scope"] == ["read:user user:email offline_access"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["state"] == ["signed-github-state"]
    assert "server-only-secret" not in url


def test_github_identity_fields_use_numeric_id_and_login():
    assert oauth._identity_fields("github", {
        "id": 12345, "login": "shopno-dev", "name": "Shopno Developer"
    }) == ("12345", "shopno-dev", "Shopno Developer")
