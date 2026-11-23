from app.security import is_admin


def test_realm_platform_admin_is_admin():
    assert is_admin({"realm_access": {"roles": ["platform_admin"]}})


def test_client_platform_admin_does_not_grant_administration():
    assert not is_admin({"resource_access": {"api-service": {"roles": ["platform_admin"]}}})


def test_explicit_empty_realm_roles_blocks_flat_aggregate_fallback():
    assert not is_admin({"roles": ["platform_admin"], "realm_roles": [], "resource_access": {"api-service": {"roles": ["platform_admin"]}}})
