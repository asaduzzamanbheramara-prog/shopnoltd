import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./session-manager-viewer-tests.db")

from app.services.url_policy import PublicURLPolicy
from app.services.session_pool import pool
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


class BrowserURLPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocks_private_and_link_local_ip_addresses(self):
        policy = PublicURLPolicy()
        self.assertFalse(await policy.is_allowed("http://10.42.0.1/"))
        self.assertFalse(await policy.is_allowed("http://169.254.169.254/latest/meta-data/"))
        self.assertFalse(await policy.is_allowed("http://127.0.0.1:8000/"))

    async def test_blocks_non_http_schemes_and_local_names(self):
        policy = PublicURLPolicy()
        self.assertFalse(await policy.is_allowed("file:///etc/passwd"))
        self.assertFalse(await policy.is_allowed("http://kubernetes.default.svc/"))
        self.assertTrue(await policy.is_allowed("about:blank"))

    async def test_blocks_dns_names_resolving_to_private_addresses(self):
        policy = PublicURLPolicy()
        private_record = [(2, 1, 6, "", ("10.42.0.8", 443))]
        with patch("app.services.url_policy.socket.getaddrinfo", return_value=private_record):
            self.assertFalse(await policy.is_allowed("https://internal.example/"))

    async def test_allows_dns_names_resolving_only_to_public_addresses(self):
        policy = PublicURLPolicy()
        public_record = [(2, 1, 6, "", ("1.1.1.1", 443))]
        with patch("app.services.url_policy.socket.getaddrinfo", return_value=public_record):
            self.assertTrue(await policy.is_allowed("https://public.example/"))


class BrowserDownloadStorageTests(unittest.TestCase):
    def test_download_listing_and_retrieval_stay_inside_profile_storage(self):
        with tempfile.TemporaryDirectory() as root:
            download_dir = Path(root) / "downloads"
            download_dir.mkdir()
            download_id = str(uuid.uuid4())
            saved_file = download_dir / f"{download_id}__report.pdf"
            saved_file.write_bytes(b"safe test content")

            entries = pool.list_downloads(root)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["id"], download_id)
            self.assertEqual(entries[0]["filename"], "report.pdf")
            path, filename = pool.get_download(root, download_id)
            self.assertEqual(path, saved_file.resolve())
            self.assertEqual(filename, "report.pdf")

    def test_download_id_cannot_escape_profile_storage(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):
                pool.get_download(root, "../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
