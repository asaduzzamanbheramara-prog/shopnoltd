import pytest
from fastapi import HTTPException

from app.api.auth import _user_id


def test_user_id_prefers_immutable_oidc_subject():
    assert _user_id({"sub": "keycloak-user-uuid", "email": "changed@example.com", "preferred_username": "changed"}) == "keycloak-user-uuid"


@pytest.mark.parametrize("claims,expected", [
    ({"email": "legacy@example.com"}, "legacy@example.com"),
    ({"preferred_username": "legacy-user"}, "legacy-user"),
])
def test_user_id_supports_legacy_claim_fallback(claims, expected):
    assert _user_id(claims) == expected


def test_user_id_rejects_tokens_without_identity():
    with pytest.raises(HTTPException) as exc:
        _user_id({})
    assert exc.value.status_code == 401
