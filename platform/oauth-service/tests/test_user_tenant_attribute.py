from app.api.users import _with_tenant_attribute


def test_tenant_attribute_update_preserves_other_keycloak_attributes():
    current = {
        "id": "keycloak-user-id",
        "email": "user@example.com",
        "attributes": {
            "department": ["sales"],
            "locale": ["bn"],
            "tenant_id": ["old-tenant"],
        },
    }

    updated = _with_tenant_attribute(current, "new-tenant")

    assert updated["attributes"] == {
        "department": ["sales"],
        "locale": ["bn"],
        "tenant_id": ["new-tenant"],
    }
    assert current["attributes"]["tenant_id"] == ["old-tenant"]


def test_clearing_tenant_removes_only_tenant_attribute():
    current = {
        "attributes": {
            "department": ["sales"],
            "tenant_id": ["old-tenant"],
        },
    }

    updated = _with_tenant_attribute(current, None)

    assert updated["attributes"] == {"department": ["sales"]}


def test_blank_tenant_is_not_written_to_keycloak():
    updated = _with_tenant_attribute({"attributes": {"tenant_id": ["old"]}}, "  ")
    assert updated["attributes"] == {}
