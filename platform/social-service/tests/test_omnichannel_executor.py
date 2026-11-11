import base64
from email import message_from_bytes

import pytest
from app.workers.omnichannel_executor import (
    _approval_is_valid,
    _provider_request,
    _rate_limit_delay_seconds,
    _response_disposition,
)


def test_human_approval_is_required_and_service_identities_cannot_approve():
    assert _approval_is_valid({
        "request_payload": {
            "_requested_by": "user-123",
            "approval": {
                "approved": True,
                "approved_by": "user-123",
                "approved_at": "2026-10-19T12:00:00+00:00",
            }
        }
    })
    assert not _approval_is_valid({"request_payload": {"approval": {"approved": False}}})
    assert not _approval_is_valid({"request_payload": {"_requested_by": "user-456", "approval": {"approved": True, "approved_by": "user-123", "approved_at": "now"}}})
    assert not _approval_is_valid({
        "request_payload": {
            "_requested_by": "n8n-action-queue",
            "approval": {
                "approved": True,
                "approved_by": "n8n-action-queue",
                "approved_at": "2026-10-19T12:00:00+00:00",
            }
        }
    })


def test_gmail_request_requires_complete_message_and_encodes_mime():
    method, url, headers, body = _provider_request(
        "gmail", "send_message", "test-token", "account-1",
        {"to": "recipient@example.com", "subject": "Hello", "text": "Test body"},
    )
    assert method == "POST"
    assert url == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    assert headers["Authorization"] == "Bearer test-token"
    raw = body["raw"]
    message = message_from_bytes(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    assert message["To"] == "recipient@example.com"
    assert message["Subject"] == "Hello"
    assert "Test body" in message.get_payload(decode=True).decode()


def test_outlook_request_uses_graph_sendmail_contract():
    method, url, _, body = _provider_request(
        "outlook", "send_message", "test-token", "account-1",
        {"to": "recipient@example.com", "subject": "Hello", "text": "Test body"},
    )
    assert method == "POST"
    assert url == "https://graph.microsoft.com/v1.0/me/sendMail"
    assert body["message"]["toRecipients"] == [
        {"emailAddress": {"address": "recipient@example.com"}}
    ]
    assert body["saveToSentItems"] is True


def test_x_post_request_is_narrow_and_does_not_leak_token_in_body():
    method, url, headers, body = _provider_request(
        "x", "create_post", "test-token", "account-1",
        {"text": "Approved test post", "approval": {"approved": True}},
    )
    assert method == "POST"
    assert url == "https://api.x.com/2/tweets"
    assert headers["Authorization"] == "Bearer test-token"
    assert body == {"text": "Approved test post"}
    assert "test-token" not in str(body)


def test_linkedin_post_uses_connected_account_as_author():
    method, url, headers, body = _provider_request(
        "linkedin", "create_post", "test-token", "12345",
        {"text": "Approved test post", "author_type": "person"},
    )
    assert method == "POST"
    assert url == "https://api.linkedin.com/rest/posts"
    assert body["author"] == "urn:li:person:12345"
    assert body["lifecycleState"] == "PUBLISHED"
    assert headers["LinkedIn-Version"]


@pytest.mark.parametrize(
    "platform,action,payload",
    [
        ("instagram", "create_post", {"text": "not supported by this adapter"}),
        ("x", "create_post", {}),
        ("gmail", "send_message", {"to": "recipient@example.com", "subject": "x"}),
        ("linkedin", "create_post", {"text": "test", "author_type": "company"}),
    ],
)
def test_unsupported_or_invalid_requests_fail_closed(platform, action, payload):
    if (platform, action) not in {
        ("gmail", "send_message"), ("outlook", "send_message"),
        ("x", "create_post"), ("linkedin", "create_post"),
    }:
        with pytest.raises(ValueError, match="unsupported_action"):
            _provider_request(platform, action, "token", "account", payload)
    else:
        with pytest.raises(ValueError):
            _provider_request(platform, action, "token", "account", payload)



@pytest.mark.parametrize(
    "status,expected",
    [
        (200, "success"),
        (202, "success"),
        (400, "rejected"),
        (401, "unauthorized"),
        (403, "forbidden"),
        (429, "rate_limited"),
        (500, "unknown"),
        (503, "unknown"),
    ],
)
def test_provider_response_disposition_is_fail_closed(status, expected):
    assert _response_disposition(status) == expected


def test_action_names_are_normalized_before_capability_lookup():
    from app.api.omnichannel import _normalize_action
    from fastapi import HTTPException

    assert _normalize_action(" Create_Post ") == "create_post"
    with pytest.raises(HTTPException) as exc:
        _normalize_action("   ")
    assert exc.value.status_code == 400


def test_post_approval_is_bound_to_exact_content_hash():
    import hashlib

    text = "approved post"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    approved = {
        "action": "create_post",
        "request_payload": {
            "text": text,
            "_requested_by": "user-1",
            "approval": {
                "approved": True,
                "approved_by": "user-1",
                "approved_at": "2026-11-09T12:00:00+00:00",
                "content_sha256": digest,
            },
        },
    }
    assert _approval_is_valid(approved)
    approved["request_payload"]["text"] = "tampered post"
    assert not _approval_is_valid(approved)


def test_approved_mail_action_does_not_require_post_content_hash():
    action = {
        "action": "send_message",
        "request_payload": {
            "text": "mail body",
            "_requested_by": "user-1",
            "approval": {
                "approved": True,
                "approved_by": "user-1",
                "approved_at": "2026-11-09T12:00:00+00:00",
            },
        },
    }
    assert _approval_is_valid(action)


def test_rate_limit_retries_use_bounded_backoff_and_retry_after():
    assert _rate_limit_delay_seconds(None, 1) == 15
    assert _rate_limit_delay_seconds(None, 2) == 30
    assert _rate_limit_delay_seconds("120", 1) == 120
    assert _rate_limit_delay_seconds("0", 1) == 1
    assert _rate_limit_delay_seconds("invalid", 3) == 60
    assert _rate_limit_delay_seconds("99999", 1) == 900
    assert _rate_limit_delay_seconds("NaN", 2) == 30
    assert _rate_limit_delay_seconds("Infinity", 1) == 15
