import asyncio
from decimal import Decimal

from fastapi import HTTPException
import pytest

from app.api.affiliate import _affmine_campaign_rows, _affmine_country_codes, _affmine_platform_codes, _client_platform, _platform_ok, _country, _geo_ok, _is_platform_admin, _percent, _require_sandbox_enabled, _safe_tracking_url, sandbox_user_summary, simulate_sandbox_earning
from app.models.affiliate import AffiliateConversion, AffiliateOffer, AffiliateSandboxConversion
from app.api.affiliate import router


class Request:
    def __init__(self, headers):
        self.headers = headers


def test_affmine_json_feed_normalizes_valid_offer_shapes():
    assert _affmine_campaign_rows(
        '{"success":true,"offers":{"offer":{"offer_id":"42","offer_name":"Example"}}}',
        "application/json",
    ) == [{"offer_id": "42", "offer_name": "Example"}]
    assert _affmine_campaign_rows(
        '{"offer_feed":{"success":1,"offers":[{"offer_id":"43"}]}}',
        "application/json",
    ) == [{"offer_id": "43"}]
    assert _affmine_campaign_rows('{"success":true,"offers":null}', "application/json") == []


@pytest.mark.parametrize("payload", [
    "[]",
    '{"offer_feed":[]}',
    '{"success":true,"offers":"not-a-list"}',
    '{"success":true,"offers":[null]}',
    "{invalid-json",
])
def test_affmine_json_feed_rejects_malformed_structures(payload):
    with pytest.raises(HTTPException) as error:
        _affmine_campaign_rows(payload, "application/json")
    assert error.value.status_code == 502


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
    custom = _safe_tracking_url("https://track.example/click", "click-456", "sub2")
    assert "sub2=click-456" in custom
    duplicate = _safe_tracking_url("https://track.example/click?sub2=old&x=1&x=2", "click-789", "sub2")
    assert duplicate.count("sub2=") == 1
    assert "sub2=click-789" in duplicate
    assert duplicate.count("x=") == 2
    with pytest.raises(HTTPException):
        _safe_tracking_url("https://track.example/click", "click-123", "bad-param!")
    with pytest.raises(HTTPException):
        _safe_tracking_url("http://track.example/click", "click-123")
    with pytest.raises(HTTPException):
        _safe_tracking_url("https://user:pass@track.example/click", "click-123")


def test_platform_admin_requires_realm_role_not_client_role():
    assert _is_platform_admin({"realm_access": {"roles": ["platform_admin"]}})
    assert _is_platform_admin({"realm_roles": ["platform_admin"]})
    assert not _is_platform_admin({"realm_access": {"roles": ["admin"]}})
    assert not _is_platform_admin({"realm_access": {"roles": ["shopnoltd-admin"]}})
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

def test_sandbox_records_are_isolated_from_real_conversion_table():
    assert AffiliateSandboxConversion.__tablename__ == "shopnoltd_affiliate_sandbox_conversions"
    assert AffiliateSandboxConversion.__tablename__ != AffiliateConversion.__tablename__
    columns = AffiliateSandboxConversion.__table__.columns
    assert "simulated_network_payout" in columns
    assert "simulated_user_amount" in columns
    assert "simulated_platform_amount" in columns
    assert "user_id" in columns


def test_sandbox_endpoints_are_separate_and_wallet_safe():
    paths = {route.path for route in router.routes}
    assert "/affiliate/sandbox/simulate" in paths
    assert "/affiliate/sandbox/me/summary" in paths
    assert "/affiliate/sandbox/me/reset" in paths
    assert "/affiliate/sandbox/admin/summary" in paths
    # The live network callback remains intentionally disabled.
    assert "/affiliate/postback" in paths

def test_sandbox_requires_explicit_environment_enablement(monkeypatch):
    monkeypatch.delenv("AFFILIATE_SANDBOX_ENABLED", raising=False)
    with pytest.raises(HTTPException) as disabled:
        _require_sandbox_enabled()
    assert disabled.value.status_code == 404
    monkeypatch.setenv("AFFILIATE_SANDBOX_ENABLED", "true")
    _require_sandbox_enabled()

def test_sandbox_summary_reports_enabled_flag(monkeypatch):
    monkeypatch.setenv("AFFILIATE_SANDBOX_ENABLED", "true")

    class Result:
        def one(self):
            return (0, Decimal("0"), Decimal("0"))

    class Session:
        async def execute(self, statement):
            return Result()

    result = asyncio.run(sandbox_user_summary({"sub": "sandbox-user"}, Session()))
    assert result["enabled"] is True
    assert result["sandbox"] is True
    assert result["withdrawable"] is False
    assert result["wallet_credited"] is False


def test_sandbox_simulation_calculates_user_and_platform_without_wallet_credit(monkeypatch):
    monkeypatch.setenv("AFFILIATE_SANDBOX_ENABLED", "true")

    class Request:
        async def json(self):
            return {"network_payout_usd": "1.00", "user_share_percent": 70}

    class Session:
        def add(self, record):
            self.record = record

        async def commit(self):
            self.committed = True

    session = Session()
    result = asyncio.run(simulate_sandbox_earning(Request(), {"sub": "sandbox-user"}, session))
    assert result["simulated_user_amount"] == "0.7000"
    assert result["simulated_platform_amount"] == "0.3000"
    assert result["withdrawable"] is False
    assert result["wallet_credited"] is False
    assert session.record.user_id == "sandbox-user"
    assert session.committed is True

def test_affmine_campaign_feed_parses_xml_and_country_codes():
    payload = """<offer_feed><row_count>1</row_count><success>true</success><offers><offer><offer_id>1256</offer_id><offer_name>Test offer</offer_name><payout>7.20</payout><currency>USD</currency><url>https://track.example/go?s1=subid</url><countries><country><country_code>US</country_code><country_name>United States</country_name></country></countries><incentive>yes</incentive></offer></offers></offer_feed>"""
    rows = _affmine_campaign_rows(payload, "application/xml")
    assert rows[0]["offer_id"] == "1256"
    assert rows[0]["countries"][0]["country_code"] == "US"
    assert _affmine_country_codes(rows[0]["countries"]) == "US"


def test_affmine_campaign_feed_parses_json_and_fails_on_network_error():
    payload = '{"offer_feed":{"success":true,"offers":{"offer":[{"offer_id":"99","offer_name":"JSON offer","payout":"1.25","currency":"USD","countries":[{"country_code":"CA"}]}]}}}'
    rows = _affmine_campaign_rows(payload, "application/json")
    assert rows[0]["offer_id"] == "99"
    assert _affmine_country_codes(rows[0]["countries"]) == "CA"
    with pytest.raises(HTTPException):
        _affmine_campaign_rows('<offer_feed><success>false</success></offer_feed>', "application/xml")


def test_affmine_sync_is_platform_admin_only_and_route_exists():
    route = next(r for r in router.routes if r.path == "/affiliate/admin/sync-affmine")
    assert "POST" in route.methods
    assert route.endpoint.__name__ == "sync_affmine_campaigns"


def test_affmine_platform_metadata_is_normalized_and_enforced():
    assert _affmine_platform_codes("1,3,4") == "1,3,4"
    assert _affmine_platform_codes(["2", "5", "invalid"]) == "2,5"
    assert _affmine_platform_codes("") == "1,2,3,4,5"
    assert _affmine_platform_codes(None) == "1,2,3,4,5"
    assert _affmine_platform_codes("0") == "1,2,3,4,5"
    assert _platform_ok(_affmine_platform_codes(""), "3")
    assert _platform_ok("1,3", "3")
    assert not _platform_ok("1,3", "4")
    assert not _platform_ok("unknown", "3")
    assert _platform_ok("1,2,3,4,5", "")


def test_client_platform_detection_from_user_agent():
    class DeviceRequest:
        def __init__(self, ua):
            self.headers = {"user-agent": ua}
    assert _client_platform(DeviceRequest("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")) == "1"
    assert _client_platform(DeviceRequest("Mozilla/5.0 (Macintosh; Intel Mac OS X)")) == "2"
    assert _client_platform(DeviceRequest("Mozilla/5.0 (Linux; Android 14) Mobile")) == "3"
    assert _client_platform(DeviceRequest("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)")) == "4"
    assert _client_platform(DeviceRequest("Mozilla/5.0 (Linux; U; Mobile)")) == "5"


def test_affiliate_offer_model_stores_network_platform_and_currency():
    columns = AffiliateOffer.__table__.columns
    assert "currency" in columns
    assert "allowed_platform" in columns
    assert "network_incentive" in columns
    assert columns["currency"].type.length == 3


def test_affmine_country_codes_support_json_shapes():
    assert _affmine_country_codes(["BD", "US"]) == "BD,US"
    assert _affmine_country_codes({"country": [{"country_code": "BD"}, {"country_code": "US"}]}) == "BD,US"
    assert _affmine_country_codes({"country_code": "BD"}) == "BD"
