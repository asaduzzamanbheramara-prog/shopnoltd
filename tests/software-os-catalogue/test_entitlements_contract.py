import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "docs/universal-software-os-center/entitlements-response.schema.json"


class EntitlementsResponseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema, format_checker=FormatChecker())

    def assert_valid(self, payload):
        self.assertEqual(list(self.validator.iter_errors(payload)), [])

    def assert_invalid(self, payload):
        self.assertTrue(list(self.validator.iter_errors(payload)))

    def test_empty_entitlement_list_is_valid(self):
        self.assert_valid({"schema_version": 1, "entitlements": []})

    def test_active_entitlement_contract_is_valid(self):
        self.assert_valid({
            "schema_version": 1,
            "entitlements": [{
                "product_id": "software-os-center-premium",
                "status": "active",
                "valid_from": "2026-10-14T00:00:00Z",
                "valid_until": "2026-11-14T00:00:00Z",
            }],
        })

    def test_rejects_unknown_fields_that_could_be_misread_as_authority(self):
        self.assert_invalid({
            "schema_version": 1,
            "is_paid": True,
            "entitlements": [],
        })

    def test_rejects_non_active_status_in_active_entitlement_list(self):
        self.assert_invalid({
            "schema_version": 1,
            "entitlements": [{
                "product_id": "software-os-center-premium",
                "status": "pending",
                "valid_from": "2026-10-14T00:00:00Z",
                "valid_until": None,
            }],
        })

    def test_rejects_invalid_timestamp(self):
        self.assert_invalid({
            "schema_version": 1,
            "entitlements": [{
                "product_id": "software-os-center-premium",
                "status": "active",
                "valid_from": "not-a-date",
                "valid_until": None,
            }],
        })

    def test_rejects_untrusted_authority_fields_inside_entitlement(self):
        self.assert_invalid({
            "schema_version": 1,
            "entitlements": [{
                "product_id": "software-os-center-premium",
                "status": "active",
                "valid_from": "2026-10-14T00:00:00Z",
                "valid_until": None,
                "amount_paid": 1,
                "payment_confirmed": True,
            }],
        })


if __name__ == "__main__":
    unittest.main()
