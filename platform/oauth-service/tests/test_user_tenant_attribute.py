from app.api.users import _keycloak_user_representation, _with_tenant_attribute


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



def test_admin_created_user_gets_the_same_tenant_attribute_as_oauth_mirror():
    representation = _keycloak_user_representation(
        email="owner@example.com",
        name="Tenant Owner",
        password="not-a-real-password",
        tenant_id=" tenant-123 ",
    )

    assert representation["email"] == "owner@example.com"
    assert representation["username"] == "owner@example.com"
    assert representation["attributes"]["tenant_id"] == ["tenant-123"]
    assert representation["credentials"] == [
        {"type": "password", "value": "not-a-real-password", "temporary": False}
    ]


def test_admin_created_unscoped_user_does_not_receive_a_guessed_tenant():
    representation = _keycloak_user_representation(
        email="admin@example.com",
        name="Platform Admin",
        password="",
        tenant_id=None,
    )

    assert "tenant_id" not in representation["attributes"]
    assert representation["credentials"] == []


def test_admin_created_user_does_not_receive_blank_tenant_claim():
    representation = _keycloak_user_representation(
        email="user@example.com",
        name="User",
        password="",
        tenant_id="   ",
    )

    assert "tenant_id" not in representation["attributes"]
