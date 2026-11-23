import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "frontend/software-os-center.html"
PACKAGED_PAGE = ROOT / "platform/shopnoltd-web/public/software-os-center.html"


class CommerceStorefrontTests(unittest.TestCase):
    def test_packaged_page_matches_source_page(self):
        self.assertEqual(PAGE.read_bytes(), PACKAGED_PAGE.read_bytes())

    def test_paid_services_are_present_with_quote_before_work_language(self):
        page = PAGE.read_text(encoding="utf-8")
        for label in ("Operating system installation", "Startup repair &amp; recovery", "Software, drivers &amp; applications", "Bootable USB &amp; recovery media", "Phone, tablet &amp; other device support", "Technical troubleshooting", "Business IT care"):
            self.assertIn(label, page)
        self.assertIn("Custom quote before work", page)
        self.assertIn("full price before any paid work begins", page)

    def test_quote_request_is_transparent_and_does_not_claim_submission(self):
        page = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="service-quote-form"', page)
        self.assertIn("mailto:support@shopnoltd.dpdns.org", page)
        self.assertIn("has not received it until you send it", page)
        self.assertIn("No payment is collected on this page", page)

    def test_page_is_branded_as_a_service_center_not_a_catalogue_preview(self):
        page = PAGE.read_text(encoding="utf-8")
        self.assertIn("<title>Software &amp; OS Services Center | Shopnoltd</title>", page)
        self.assertIn("<h1>Software &amp; OS Services Center</h1>", page)
        self.assertIn("Shopnoltd Software &amp; OS Services Center.", page)
        self.assertNotIn("Catalogue preview", page)

    def test_quote_uses_the_published_shopnoltd_support_address(self):
        page = PAGE.read_text(encoding="utf-8")
        contact = (ROOT / "platform/web-portal/src/pages/Contact.jsx").read_text(encoding="utf-8")
        self.assertIn("mailto:support@shopnoltd.dpdns.org", page)
        self.assertIn("const SUPPORT_EMAIL = 'support@shopnoltd.dpdns.org'", contact)

    def test_no_browser_side_payment_or_entitlement_unlock(self):
        page = PAGE.read_text(encoding="utf-8")
        self.assertNotIn("/billing/checkout", page)
        self.assertNotIn("payment_confirmed", page)
        self.assertNotIn("is_paid", page)


if __name__ == "__main__":
    unittest.main()
