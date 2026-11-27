from app.core.integration_catalog import (
    EXISTING_OMNICHANNEL_PLATFORMS,
    INTEGRATION_CATALOG,
    list_integrations,
)


def test_catalog_has_unique_ids_and_required_metadata():
    ids = [item["id"] for item in INTEGRATION_CATALOG]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 90
    for item in INTEGRATION_CATALOG:
        assert item["name"]
        assert item["category"]
        assert item["connection_type"]
        assert item["status"] in {"existing_connector_flow", "catalog_only"}
        assert item["executable_actions"] == []
        assert item["requires_provider_authorization"] is True


def test_only_existing_omnichannel_platforms_are_marked_as_existing_flow():
    marked = {item["id"] for item in INTEGRATION_CATALOG if item["status"] == "existing_connector_flow"}
    assert marked == EXISTING_OMNICHANNEL_PLATFORMS


def test_catalog_category_filter_is_case_insensitive():
    result = list_integrations(category="aFfIlIaTe")
    assert result["total"] > 0
    assert all(item["category"] == "Affiliate" for item in result["integrations"])


def test_catalog_search_matches_name_and_provider_identity_warning():
    result = list_integrations(query="Affmine")
    assert result["total"] == 1
    item = result["integrations"][0]
    assert item["status"] == "catalog_only"
    assert "must be verified" in item["note"]


def test_catalog_search_and_category_can_be_combined():
    result = list_integrations(category="Commerce", query="shopify")
    assert result["total"] == 1
    assert result["integrations"][0]["id"] == "shopify"


def test_empty_filter_returns_complete_catalog_and_categories():
    result = list_integrations()
    assert result["total"] == result["catalog_total"] == len(INTEGRATION_CATALOG)
    assert "Commerce" in result["categories"]
    assert "Cloud & Hosting" in result["categories"]
