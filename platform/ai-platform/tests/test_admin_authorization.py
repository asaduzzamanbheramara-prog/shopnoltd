from app.core.security import user_roles


def test_platform_roles_exclude_all_client_roles():
    assert user_roles({
        "roles": ["customer"],
        "realm_access": {"roles": ["tenant_owner"]},
        "resource_access": {
            "ai-platform": {"roles": ["platform_admin", "admin"]},
            "other-client": {"roles": ["platform_admin"]},
        },
    }) == {"customer", "tenant_owner"}


def test_explicit_empty_realm_roles_block_aggregate_fallback():
    assert user_roles({
        "roles": ["platform_admin"],
        "realm_roles": [],
        "resource_access": {"ai-platform": {"roles": ["platform_admin"]}},
    }) == set()
