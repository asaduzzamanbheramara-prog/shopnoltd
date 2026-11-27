from app.core.security import realm_roles


def test_client_roles_do_not_grant_payment_platform_admin():
    user = {
        "roles": ["admin", "platform_admin"],
        "realm_roles": [],
        "realm_access": {"roles": []},
        "resource_access": {
            "shopnoltd-web": {"roles": ["admin", "platform_admin"]},
            "payment-service": {"roles": ["admin"]},
        },
    }
    assert realm_roles(user) == set()


def test_realm_platform_admin_is_authoritative():
    user = {
        "roles": ["customer"],
        "realm_roles": ["platform_admin"],
        "realm_access": {"roles": ["tenant_owner"]},
        "resource_access": {"shopnoltd-web": {"roles": ["admin"]}},
    }
    assert realm_roles(user) == {"platform_admin", "tenant_owner"}


def test_legacy_flat_realm_role_claim_is_supported():
    assert realm_roles({"roles": ["platform_admin"]}) == {"platform_admin"}
