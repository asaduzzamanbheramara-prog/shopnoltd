import unittest

from app.services.action_executor import telegram_message_payload


class TelegramPayloadTests(unittest.TestCase):
    def test_telegram_payload_uses_target_and_text(self):
        self.assertEqual(
            telegram_message_payload("send_message", {"text": "hello"}, "chat-123"),
            {"chat_id": "chat-123", "text": "hello"},
        )

    def test_telegram_payload_accepts_payload_chat_id(self):
        self.assertEqual(
            telegram_message_payload("send_message", {"chat_id": "chat-1", "message": "hello"}, None),
            {"chat_id": "chat-1", "text": "hello"},
        )

    def test_unsupported_or_invalid_actions_fail_closed(self):
        cases = [
            ("like", {"text": "hello"}, "chat-1"),
            ("create_post", {"text": "hello"}, "chat-1"),
            ("send_message", {}, "chat-1"),
            ("send_message", {"text": "hello"}, None),
            ("send_message", {"text": "x" * 4097}, "chat-1"),
        ]
        for action, payload, target in cases:
            with self.subTest(action=action, payload_keys=list(payload)):
                with self.assertRaises(ValueError):
                    telegram_message_payload(action, payload, target)


if __name__ == "__main__":
    unittest.main()
