import pytest
from fastapi import HTTPException

from app.api.drive import owned_key, owner_prefix


USER_A = {"sub": "account_A-123"}
USER_B = {"sub": "account_B-456"}


def test_owner_prefix_is_derived_from_verified_subject():
    assert owner_prefix(USER_A) == "users/account_A-123/"
    assert owner_prefix(USER_B) == "users/account_B-456/"


def test_owned_key_keeps_objects_inside_the_calling_users_prefix():
    assert owned_key(USER_A, "reports/annual.pdf") == "users/account_A-123/reports/annual.pdf"
    assert owned_key(USER_B, "reports/annual.pdf") == "users/account_B-456/reports/annual.pdf"
    assert owned_key(USER_A, "reports/annual.pdf") != owned_key(USER_B, "reports/annual.pdf")


@pytest.mark.parametrize(
    "key",
    [
        "",
        "/absolute.txt",
        "../other-account/secret.txt",
        "folder/../secret.txt",
        "./secret.txt",
        "folder//secret.txt",
        "folder/",
        r"folder\\secret.txt",
        "bad\x00name.txt",
    ],
)
def test_owned_key_rejects_malformed_or_traversal_paths(key):
    with pytest.raises(HTTPException) as exc:
        owned_key(USER_A, key)
    assert exc.value.status_code == 400


def test_owner_prefix_rejects_missing_or_unsafe_subject():
    for user in ({}, {"sub": ""}, {"sub": "../other"}, {"sub": "account/other"}):
        with pytest.raises(HTTPException) as exc:
            owner_prefix(user)
        assert exc.value.status_code == 403


def test_owned_key_enforces_utf8_path_length():
    with pytest.raises(HTTPException) as exc:
        owned_key(USER_A, "a" * 481)
    assert exc.value.status_code == 400
