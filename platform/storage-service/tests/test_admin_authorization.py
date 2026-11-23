from app.core.security import realm_roles


def test_realm_roles_exclude_every_client_role():
    assert realm_roles({"roles": ["customer"], "realm_access": {"roles": ["tenant_owner"]}, "resource_access": {"storage-service": {"roles": ["platform_admin", "admin"]}, "other-client": {"roles": ["tenant_owner"]}}}) == {"customer", "tenant_owner"}


def test_explicit_empty_realm_roles_are_authoritative():
    assert realm_roles({"roles": ["platform_admin"], "realm_roles": [], "resource_access": {"storage-service": {"roles": ["platform_admin"]}}}) == set()


def test_profile_video_admin_guard_rejects_client_scoped_admin():
    from app.api.profile_videos import _admin_roles

    assert not _admin_roles({"resource_access": {"storage-service": {"roles": ["platform_admin"]}}})
    assert _admin_roles({"realm_access": {"roles": ["platform_admin"]}})
