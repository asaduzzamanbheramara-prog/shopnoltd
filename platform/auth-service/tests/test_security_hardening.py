import unittest
from unittest.mock import AsyncMock, patch

from app.core import security
from app.core.config import settings


class AuthenticationSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_verifier_pins_rs256_and_validates_issuer_and_audience(self):
        with (
            patch.object(security.jwt, "get_unverified_header", return_value={"kid": "key-1"}),
            patch.object(
                security,
                "_jwks",
                new=AsyncMock(return_value={"keys": [{"kid": "key-1", "alg": "RS256"}]}),
            ),
            patch.object(security.jwt, "decode", return_value={"sub": "user-1"}) as decode,
        ):
            claims = await security.verify_token("opaque-test-token")

        self.assertEqual(claims["sub"], "user-1")
        kwargs = decode.call_args.kwargs
        self.assertEqual(kwargs["algorithms"], ["RS256"])
        self.assertEqual(kwargs["issuer"], settings.keycloak_issuer)
        self.assertEqual(kwargs["audience"], settings.keycloak_audience)
        self.assertTrue(kwargs["options"]["verify_iss"])
        self.assertTrue(kwargs["options"]["verify_aud"])

    async def test_client_role_cannot_grant_platform_admin(self):
        client_only_admin = {
            "sub": "user-1",
            "resource_access": {"shopnoltd-web": {"roles": ["admin", "platform_admin"]}},
        }
        with patch.object(
            security, "verify_token", new=AsyncMock(return_value=client_only_admin)
        ):
            with self.assertRaises(PermissionError):
                await security.verify_token_admin("opaque-test-token")

    async def test_realm_platform_admin_is_accepted(self):
        realm_admin = {"sub": "user-1", "realm_access": {"roles": ["platform_admin"]}}
        with patch.object(
            security, "verify_token", new=AsyncMock(return_value=realm_admin)
        ):
            result = await security.verify_token_admin("opaque-test-token")
        self.assertEqual(result, realm_admin)


if __name__ == "__main__":
    unittest.main()
