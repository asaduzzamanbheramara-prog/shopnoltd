from fastapi import HTTPException
import pytest

from app.api.affiliate import _country, _geo_ok, _is_platform_admin, _safe_tracking_url


class Request:
    def __init__(self, headers):
        self.headers = headers


def test_country_requires_cloudflare_country_header():
    assert _country(Request({"cf-ipcountry": "BD"})) == "BD"
    assert _country(Request({"cf-ipcountry": "XX"})) == ""
    assert _country(Request({"x-country": "BD"})) == ""


def test_geo_filter_fails_closed_for_restricted_offer():
    assert _geo_ok("US,CA", "US")
    assert not _geo_ok("US,CA", "BD")
    assert not _geo_ok("US,CA", "")
    assert _geo_ok("WORLDWIDE", "")


def test_tracking_url_requires_https_and_sets_click_id():
    result = _safe_tracking_url("https://track.example/click?x=1", "click-123")
    assert "s1=click-123" in result
    assert "x=1" in result
    with pytest.raises(HTTPException):
        _safe_tracking_url("http://track.example/click", "click-123")


def test_platform_admin_requires_realm_role():
    assert _is_platform_admin({"realm_access": {"roles": ["platform_admin"]}})
    assert _is_platform_admin({"realm_roles": ["platform_admin"]})
    assert not _is_platform_admin({
        "roles": ["platform_admin"],
        "resource_access": {"client": {"roles": ["platform_admin"]}},
    })
