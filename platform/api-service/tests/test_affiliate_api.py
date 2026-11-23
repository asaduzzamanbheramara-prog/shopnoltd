from fastapi import HTTPException
import pytest

from app.api.affiliate import _country, _geo_ok, _is_platform_admin, _percent, _safe_tracking_url
from app.models.affiliate import AffiliateConversion, AffiliateOffer\nfrom app.api.affiliate import router


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
    with pytest.raises(HTTPException):
        _safe_tracking_url("https://user:pass@track.example/click", "click-123")


def test_platform_admin_requires_realm_role_not_client_role():
    assert _is_platform_admin({"realm_access": {"roles": ["platform_admin"]}})
    assert _is_platform_admin({"realm_roles": ["platform_admin"]})
    assert not _is_platform_admin({
        "roles": ["platform_admin"],
        "resource_access": {"client": {"roles": ["platform_admin"]}},
    })


def test_commission_split_is_bounded_and_preserves_platform_share():
    assert _percent(70) == 70
    assert 100 - _percent(70) == 30
    assert _percent(0) == 0
    assert _percent(90) == 90
    for value in (-1, 91, "not-a-number", 70.5):
        with pytest.raises(HTTPException):
            _percent(value)


def test_offer_default_split_benefits_user_and_platform():
    assert AffiliateOffer.__table__.c.user_share_percent.default.arg == 70
    assert AffiliateConversion.__table__.c.user_share_percent.default.arg == 70
    assert "shopnoltd_affiliate_offers" == AffiliateOffer.__tablename__
    assert "shopnoltd_affiliate_conversions" == AffiliateConversion.__tablename__


def test_conversion_model_keeps_network_payment_and_fx_snapshots():
    columns = AffiliateConversion.__table__.columns
    assert "network_payout" in columns
    assert "user_amount" in columns
    assert "platform_amount" in columns
    assert "fx_rate_usd_bdt" in columns
    assert "user_amount_bdt" in columns
    assert "payout_received" in columns
    assert "settled_at" in columns

def test_affiliate_router_exposes_user_and_admin_automation_endpoints():
    paths = {route.path for route in router.routes}
    assert "/affiliate/offers" in paths
    assert "/affiliate/offers/{offer_id}/start" in paths
    assert "/affiliate/me/summary" in paths
    assert "/affiliate/rates/usd-bdt" in paths
    assert "/affiliate/admin/offers" in paths
    assert "/affiliate/admin/offers/{offer_id}/commission" in paths
    assert "/affiliate/admin/offers/{offer_id}/eligibility" in paths
    assert "/affiliate/admin/summary" in paths
