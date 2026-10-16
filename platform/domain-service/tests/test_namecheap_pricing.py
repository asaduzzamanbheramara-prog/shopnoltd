import unittest
from decimal import Decimal
from xml.etree import ElementTree

from app.services.registrars.namecheap import NamecheapAdapter
from app.services.domain_pricing import registration_quote


def pricing_xml(prices: str) -> ElementTree.Element:
    return ElementTree.fromstring(
        f"""<ApiResponse xmlns="http://api.namecheap.com/xml.response" Status="OK">
          <CommandResponse>
            <UserGetPricingResult>
              <ProductType Name="DOMAIN">
                <ProductCategory Name="REGISTER">
                  <Product Name="com">
                    {prices}
                  </Product>
                </ProductCategory>
              </ProductType>
            </UserGetPricingResult>
          </CommandResponse>
        </ApiResponse>"""
    )


class NamecheapPricingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.adapter = NamecheapAdapter(
            api_key="test-key",
            username="test-user",
            client_ip="192.0.2.10",
            sandbox=True,
        )

    async def test_returns_exact_requested_duration(self):
        root = pricing_xml(
            '<Price Duration="1" DurationType="YEAR" YourPrice="12.99" Currency="USD" />'
            '<Price Duration="2" DurationType="YEAR" YourPrice="24.50" Currency="USD" />'
        )

        async def fake_call(command, params, operation):
            self.assertEqual(command, "namecheap.users.getPricing")
            self.assertEqual(params["ProductName"], "com")
            return root

        self.adapter._call = fake_call
        result = await self.adapter.get_pricing(".com", years=2)
        self.assertEqual(result, {
            "tld": "com",
            "years": 2,
            "price": 24.50,
            "currency": "USD",
        })

    async def test_fails_closed_when_exact_duration_is_missing(self):
        root = pricing_xml(
            '<Price Duration="1" DurationType="YEAR" YourPrice="12.99" Currency="USD" />'
        )

        async def fake_call(command, params, operation):
            return root

        self.adapter._call = fake_call
        with self.assertRaisesRegex(RuntimeError, "no 2-year price returned for .com"):
            await self.adapter.get_pricing("com", years=2)

    async def test_does_not_treat_other_duration_as_exact_when_duration_type_differs(self):
        root = pricing_xml(
            '<Price Duration="2" DurationType="MONTH" YourPrice="5.00" Currency="USD" />'
        )

        async def fake_call(command, params, operation):
            return root

        self.adapter._call = fake_call
        with self.assertRaisesRegex(RuntimeError, "no 2-year price returned for .com"):
            await self.adapter.get_pricing("com", years=2)


class RegistrationQuoteTests(unittest.TestCase):
    def test_regular_quote_uses_exact_duration_price_and_currency(self):
        amount, currency = registration_quote(
            {"available": True, "premium": False},
            {"price": "49.95", "currency": "USD", "years": 3},
            years=3,
        )
        self.assertEqual(amount, Decimal("49.95"))
        self.assertEqual(currency, "USD")

    def test_multi_year_premium_quote_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "multi-year premium quotes are unavailable"):
            registration_quote(
                {"available": True, "premium": True, "premium_price": "120.00"},
                {"price": "12.00", "currency": "USD", "years": 3},
                years=3,
            )

    def test_non_positive_price_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-positive"):
            registration_quote(
                {"available": True, "premium": False},
                {"price": "0", "currency": "USD", "years": 1},
                years=1,
            )

    def test_quote_duration_must_match_requested_duration(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            registration_quote(
                {"available": True, "premium": False},
                {"price": "49.95", "currency": "USD", "years": 1},
                years=3,
            )


if __name__ == "__main__":
    unittest.main()
