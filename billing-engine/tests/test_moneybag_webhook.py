import hashlib
import hmac
import os
import sys
import tempfile
import time
import unittest


DB_FILE = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
DB_FILE.close()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE.name}"
os.environ["MONEYBAG_WEBHOOK_SECRET"] = "test-moneybag-webhook-secret"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.moneybag_routes import _record_webhook_event, _verify_webhook_signature  # noqa: E402
from app.models import MoneybagWebhookEvent  # noqa: E402


class MoneybagWebhookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_event_identity_is_persisted_and_duplicate_is_detected(self):
        body = b'{"event_id":"evt_test","data":{"transaction_id":"txn_test"}}'
        event = _record_webhook_event(
            self.db,
            event_id="evt_test",
            event_type="payment.success",
            transaction_id="txn_test",
            order_id="order_test",
            raw_body=body,
        )
        self.assertIsNotNone(event)
        self.db.commit()

        duplicate = _record_webhook_event(
            self.db,
            event_id="evt_test",
            event_type="payment.success",
            transaction_id="txn_test",
            order_id="order_test",
            raw_body=body,
        )
        self.assertIsNone(duplicate)
        self.assertEqual(
            self.db.query(MoneybagWebhookEvent).filter_by(event_id="evt_test").count(),
            1,
        )

    def test_signature_uses_timestamp_and_raw_body(self):
        body = b'{"event_id":"evt_signature"}'
        timestamp = str(int(time.time()))
        signed = timestamp.encode() + b"." + body
        signature = "sha256=" + hmac.new(
            os.environ["MONEYBAG_WEBHOOK_SECRET"].encode(),
            signed,
            hashlib.sha256,
        ).hexdigest()
        _verify_webhook_signature(body, signature, timestamp)


if __name__ == "__main__":
    unittest.main()
