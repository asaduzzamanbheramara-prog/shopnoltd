import pytes
from pydantic import ValidationErro

from app.api.omnichannel import ConnectionIn


def _payload(**overrides):
    payload = {
        "platform": "x",
        "platform_account_id": "x-user-123",
        "metadata": {"profile_url": "https://x.com/creator"},
    }
    payload.update(overrides)
    return payload


def test_secret_manager_reference_is_accepted():
    item = ConnectionIn(**_payload(access_token_ref="vault://shopnoltd/x/access-token"))
    assert item.access_token_ref == "vault://shopnoltd/x/access-token"


@pytest.mark.parametrize("value", [
    "actual-token-value",
    "Bearer eyJhbGciOi...",
    "ya29.some-google-token",
    "EAAfacebooktoken",
])
def test_raw_credentials_are_rejected_from_reference_fields(value):
    with pytest.raises(ValidationError):
        ConnectionIn(**_payload(access_token_ref=value))


def test_raw_credentials_are_rejected_from_metadata():
    with pytest.raises(ValidationError):
        ConnectionIn(**_payload(metadata={"access_token": "secret-token"}))
