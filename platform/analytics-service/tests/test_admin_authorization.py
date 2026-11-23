from app.core.security import realm_roles


def test_realm_roles_exclude_every_client_role():
    assert realm_roles({"roles": ["customer"], "realm_access": {"roles": ["tenant_owner"]}, "resource_access": {"api-service": {"roles": ["platform_admin", "admin"]}, "other-client": {"roles": ["tenant_owner"]}}}) == {"customer", "tenant_owner"}


def test_explicit_empty_realm_roles_are_authoritative():
    assert realm_roles({"roles": ["platform_admin"], "realm_roles": [], "resource_access": {"analytics-service": {"roles": ["platform_admin"]}}}) == set()
