import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./session-manager-viewer-tests.db")

from app.routers.viewer import (
    TICKET_TTL_SECONDS,
    _consume_ticket,
    _issue_ticket,
    _tickets,
    _viewers,
    revoke_profile_viewers,
)


class ViewerTicketTests(unittest.TestCase):
    def setUp(self):
        _tickets.clear()
        _viewers.clear()

    def test_ticket_is_bound_to_profile_and_owner_and_is_one_time(self):
        ticket = _issue_ticket("profile-a", "keycloak-subject-a", now=100)
        record = _consume_ticket(ticket, "profile-a", now=101)
        self.assertEqual(record["owner"], "keycloak-subject-a")
        self.assertIsNone(_consume_ticket(ticket, "profile-a", now=102))

    def test_expired_ticket_is_rejected(self):
        ticket = _issue_ticket("profile-a", "subject-a", now=100)
        self.assertIsNone(
            _consume_ticket(ticket, "profile-a", now=100 + TICKET_TTL_SECONDS + 1)
        )

    def test_ticket_cannot_be_exchanged_for_another_profile(self):
        ticket = _issue_ticket("profile-a", "subject-a", now=100)
        self.assertIsNone(_consume_ticket(ticket, "profile-b", now=101))
        self.assertIsNone(_consume_ticket(ticket, "profile-a", now=102))

    def test_close_revokes_profile_viewer_cookies(self):
        _viewers["viewer-one"] = {"profile_id": "profile-a", "owner": "subject-a", "expires_at": 999}
        _viewers["viewer-two"] = {"profile_id": "profile-b", "owner": "subject-b", "expires_at": 999}
        revoke_profile_viewers("profile-a")
        self.assertNotIn("viewer-one", _viewers)
        self.assertIn("viewer-two", _viewers)


if __name__ == "__main__":
    unittest.main()
