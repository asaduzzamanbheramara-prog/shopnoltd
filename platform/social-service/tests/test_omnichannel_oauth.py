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
