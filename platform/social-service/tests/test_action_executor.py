import pytest

from app.services.action_executor import telegram_message_payload


def test_telegram_payload_uses_target_and_text():
    assert telegram_message_payload("send_message", {"text": "hello"}, "chat-123") == {
        "chat_id": "chat-123",
        "text": "hello",
    }


def test_telegram_payload_accepts_payload_chat_id():
    assert telegram_message_payload("send_message", {"chat_id": "chat-1", "message": "hello"}, None) == {
        "chat_id": "chat-1",
        "text": "hello",
    }


@pytest.mark.parametrize("action,payload,target", [
    ("like", {"text": "hello"}, "chat-1"),
    ("create_post", {"text": "hello"}, "chat-1"),
    ("send_message", {}, "chat-1"),
    ("send_message", {"text": "hello"}, None),
    ("send_message", {"text": "x" * 4097}, "chat-1"),
])
def test_unsupported_or_invalid_action_fails_closed(action, payload, target):
    with pytest.raises(ValueError):
        telegram_message_payload(action, payload, target)
