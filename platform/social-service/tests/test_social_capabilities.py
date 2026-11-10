import pytest
from app.core.social_capabilities import (
    SIDE_EFFECT_ACTIONS,
    SUPPORTED_PROVIDER_ACTIONS,
    is_supported_provider_action,
    requires_human_approval,
)


def test_supported_actions_are_a_subset_of_human_approved_side_effects():
    assert SUPPORTED_PROVIDER_ACTIONS == {
        ("gmail", "send_message"),
        ("outlook", "send_message"),
        ("x", "create_post"),
        ("linkedin", "create_post"),
    }
    assert all(action in SIDE_EFFECT_ACTIONS for _, action in SUPPORTED_PROVIDER_ACTIONS)


@pytest.mark.parametrize(
    "platform,action",
    [
        ("instagram", "create_post"),
        ("facebook", "comment"),
        ("x", "like"),
        ("linkedin", "follow"),
        ("youtube", "live"),
        ("tiktok", "share"),
        ("whatsapp", "send_message"),
    ],
)
def test_unimplemented_provider_side_effects_fail_closed(platform, action):
    assert requires_human_approval(action)
    assert not is_supported_provider_action(platform, action)


def test_supported_action_normalization_is_case_and_space_insensitive():
    assert is_supported_provider_action(" X ", " CREATE_POST ")
    assert is_supported_provider_action("LinkedIn", "create_post")


def test_oauth_encryption_key_must_be_a_valid_fernet_key():
    from cryptography.fernet import Fernet
    from app.core.config import Settings

    valid = Settings(provider_oauth_encryption_key=Fernet.generate_key().decode())
    invalid = Settings(provider_oauth_encryption_key="not-a-fernet-key")
    assert valid.provider_oauth_encryption_ready is True
    assert invalid.provider_oauth_encryption_ready is False
