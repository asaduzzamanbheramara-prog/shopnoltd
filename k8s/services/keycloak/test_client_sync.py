import importlib.util
import urllib.parse
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("client-sync.py")
SPEC = importlib.util.spec_from_file_location("client_sync", MODULE_PATH)
client_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(client_sync)


class LoginBrokerFlowTests(TestCase):
    def test_social_providers_get_separate_login_and_signup_aliases(self):
        environment = {
            "GOOGLE_CLIENT_ID": "google-id",
            "GOOGLE_CLIENT_SECRET": "google-secret",
            "FACEBOOK_LOGIN_APP_ID": "facebook-id",
            "FACEBOOK_LOGIN_APP_SECRET": "facebook-secret",
            "GITHUB_CLIENT_ID": "github-id",
            "GITHUB_CLIENT_SECRET": "github-secret",
        }
        with patch.dict("os.environ", environment, clear=False):
            with patch.object(client_sync, "ensure_login_first_broker_flow") as ensure_flow:
                with patch.object(client_sync, "sync_social_provider", return_value=True) as sync_provider:
                    client_sync.sync_social_providers("test-token")

        ensure_flow.assert_called_once_with("test-token")
        self.assertEqual(
            [(call.args[1], call.args[3] if len(call.args) > 3 else "first broker login") for call in sync_provider.call_args_list],
            [
                ("google", client_sync.LOGIN_FIRST_BROKER_FLOW),
                ("google-signup", "first broker login"),
                ("facebook", client_sync.LOGIN_FIRST_BROKER_FLOW),
                ("facebook-signup", "first broker login"),
                ("github", client_sync.LOGIN_FIRST_BROKER_FLOW),
                ("github-signup", "first broker login"),
            ],
        )

    def test_signup_aliases_are_hidden_from_login_page_but_login_aliases_remain_visible(self):
        provider = client_sync.SOCIAL_PROVIDERS["facebook"]
        environment = {
            provider["clientIdEnv"]: "facebook-id",
            provider["clientSecretEnv"]: "facebook-secret",
        }

        for alias, expected_hide in (("facebook", False), ("facebook-signup", True)):
            requests = []

            def fake_request(method, path, token=None, body=None, form=False):
                requests.append((method, path, body))
                if method == "GET":
                    return 404, None
                if method == "POST":
                    return 201, None
                self.fail("Unexpected Keycloak API call: {} {}".format(method, path))

            with patch.dict("os.environ", environment, clear=False):
                with patch.object(client_sync, "request", side_effect=fake_request):
                    self.assertTrue(
                        client_sync.sync_social_provider("test-token", alias, provider)
                    )

            created = next(body for method, path, body in requests if method == "POST")
            self.assertEqual(created["hideOnLogin"], expected_hide, alias)


    def test_oauth_social_providers_do_not_trust_unverified_email_claims(self):
        for alias in ("facebook", "github"):
            provider = client_sync.SOCIAL_PROVIDERS[alias]
            environment = {
                provider["clientIdEnv"]: alias + "-id",
                provider["clientSecretEnv"]: alias + "-secret",
            }
            requests = []

            def fake_request(method, path, token=None, body=None, form=False):
                requests.append((method, path, body))
                if method == "GET":
                    return 404, None
                if method == "POST":
                    return 201, None
                self.fail("Unexpected Keycloak API call: {} {}".format(method, path))

            with patch.dict("os.environ", environment, clear=False):
                with patch.object(client_sync, "request", side_effect=fake_request):
                    self.assertTrue(
                        client_sync.sync_social_provider("test-token", alias, provider)
                    )

            created = next(body for method, path, body in requests if method == "POST")
            self.assertFalse(created["trustEmail"], alias)
            self.assertEqual(created["firstBrokerLoginFlowAlias"], "first broker login")


    def test_login_flow_updates_each_execution_using_keycloak_api_contract(self):
        top = {"id": "login-flow-id", "alias": client_sync.LOGIN_FIRST_BROKER_FLOW}
        executions = [
            {"id": "create-user", "providerId": "idp-create-user-if-unique", "requirement": "ALTERNATIVE", "level": 1},
            {"id": "confirm-link", "providerId": "idp-confirm-link", "requirement": "REQUIRED", "level": 2},
            {"id": "verify-email", "providerId": "idp-email-verification", "requirement": "ALTERNATIVE", "level": 3},
            {"id": "reauth", "providerId": "idp-username-password-form", "requirement": "REQUIRED", "level": 4},
        ]
        calls = []
        flow_reads = 0

        def fake_request(method, path, token=None, body=None, form=False):
            nonlocal flow_reads
            calls.append((method, path, body))
            if method == "GET" and path.endswith("/authentication/flows"):
                flow_reads += 1
                if flow_reads == 1:
                    return 200, [{"id": "default-flow", "alias": "first broker login"}]
                return 200, [top]
            if method == "POST" and path.endswith("/first%20broker%20login/copy"):
                return 201, None
            if method == "GET" and path.endswith("/executions"):
                return 200, [dict(item) for item in executions]
            if method == "PUT":
                self.assertIsInstance(body, dict)
                return 204, None
            self.fail("Unexpected Keycloak API call: {} {}".format(method, path))

        with patch.object(client_sync, "request", side_effect=fake_request):
            client_sync.ensure_login_first_broker_flow("test-token")

        updates = [body for method, path, body in calls if method == "PUT"]
        self.assertEqual(len(updates), 4)
        self.assertEqual(
            {item["id"]: item["requirement"] for item in updates},
            {
                "create-user": "DISABLED",
                "confirm-link": "DISABLED",
                "verify-email": "REQUIRED",
                "reauth": "DISABLED",
            },
        )
        self.assertTrue(any(method == "POST" and path.endswith("/first%20broker%20login/copy") for method, path, _ in calls))


    def test_login_flow_updates_nested_execution_returned_by_recursive_keycloak_api(self):
        top = {"id": "login-flow-id", "alias": client_sync.LOGIN_FIRST_BROKER_FLOW}
        # Keycloak's root executions endpoint returns nested authenticator entries
        # in the same list, with their nesting level represented by "level".
        executions = [
            {"id": "subflow", "displayName": "nested-flow", "authenticatorFlow": True, "flowId": "nested-id", "requirement": "REQUIRED", "level": 1},
            {"id": "create-user", "providerId": "idp-create-user-if-unique", "requirement": "ALTERNATIVE", "level": 2},
            {"id": "confirm-link", "providerId": "idp-confirm-link", "requirement": "REQUIRED", "level": 2},
            {"id": "email", "providerId": "idp-email-verification", "requirement": "ALTERNATIVE", "level": 2},
            {"id": "reauth", "providerId": "idp-username-password-form", "requirement": "REQUIRED", "level": 3},
        ]
        calls = []
        flow_reads = 0

        def fake_request(method, path, token=None, body=None, form=False):
            nonlocal flow_reads
            calls.append((method, path, body))
            if method == "GET" and path.endswith("/authentication/flows"):
                flow_reads += 1
                if flow_reads == 1:
                    return 200, [{"id": "default-flow", "alias": "first broker login"}]
                return 200, [top]
            if method == "POST" and path.endswith("/first%20broker%20login/copy"):
                return 201, None
            if method == "GET" and path.endswith("/executions"):
                return 200, [dict(item) for item in executions]
            if method == "PUT":
                self.assertIsInstance(body, dict)
                return 204, None
            self.fail("Unexpected Keycloak API call: {} {}".format(method, path))

        with patch.object(client_sync, "request", side_effect=fake_request):
            client_sync.ensure_login_first_broker_flow("test-token")

        updates = [body for method, path, body in calls if method == "PUT"]
        self.assertEqual(
            {item["id"]: item["requirement"] for item in updates},
            {
                "create-user": "DISABLED",
                "confirm-link": "DISABLED",
                "email": "REQUIRED",
                "reauth": "DISABLED",
            },
        )
        execution_reads = [
            path for method, path, _ in calls
            if method == "GET" and path.endswith("/executions")
        ]
        self.assertEqual(len(execution_reads), 1)
        self.assertIn(urllib.parse.quote(client_sync.LOGIN_FIRST_BROKER_FLOW, safe=""), execution_reads[0])




class MailApiSwaggerClientTests(TestCase):
    def test_swagger_callback_and_origin_are_allowed_for_browser_client(self):
        self.assertIn(
            "https://mail-api.shopnoltd.dpdns.org/docs/oauth2-redirect",
            client_sync.CLIENT_CONFIG["shopnoltd-web"]["redirect_uris"],
        )
        self.assertIn(
            "https://mail-api.shopnoltd.dpdns.org",
            client_sync.CLIENT_CONFIG["shopnoltd-web"]["web_origins"],
        )

    def test_mail_service_audience_mapper_is_created_for_browser_client(self):
        calls = []

        def fake_request(method, path, token=None, body=None, form=False):
            calls.append((method, path, body))
            if method == "GET":
                return 200, []
            if method == "POST":
                return 201, None
            self.fail("Unexpected Keycloak API call: {} {}".format(method, path))

        with patch.object(client_sync, "request", side_effect=fake_request):
            client_sync.sync_mail_audience_mapper("test-token", "client-uuid")

        created = next(body for method, _path, body in calls if method == "POST")
        self.assertEqual(created["name"], "mail-service-audience")
        self.assertEqual(created["protocolMapper"], "oidc-audience-mapper")
        self.assertEqual(created["config"]["included.custom.audience"], "mail-service")
        self.assertEqual(created["config"]["access.token.claim"], "true")
        self.assertEqual(created["config"]["id.token.claim"], "false")


if __name__ == "__main__":
    main()
