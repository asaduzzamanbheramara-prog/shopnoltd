import importlib.util
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
            "FACEBOOK_APP_ID": "facebook-id",
            "FACEBOOK_APP_SECRET": "facebook-secret",
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

    def test_login_flow_disables_creation_and_link_confirmation_only(self):
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
                return 204, None
            self.fail("Unexpected Keycloak API call: {} {}".format(method, path))

        with patch.object(client_sync, "request", side_effect=fake_request):
            client_sync.ensure_login_first_broker_flow("test-token")

        updates = [body for method, path, body in calls if method == "PUT"]
        self.assertEqual(len(updates), 1)
        updated = updates[0]
        self.assertEqual(next(item for item in updated if item["providerId"] == "idp-create-user-if-unique")["requirement"], "DISABLED")
        self.assertEqual(next(item for item in updated if item["providerId"] == "idp-confirm-link")["requirement"], "DISABLED")
        self.assertEqual(next(item for item in updated if item["providerId"] == "idp-email-verification")["requirement"], "ALTERNATIVE")
        self.assertEqual(next(item for item in updated if item["providerId"] == "idp-username-password-form")["requirement"], "REQUIRED")
        self.assertTrue(any(method == "POST" and path.endswith("/first%20broker%20login/copy") for method, path, _ in calls))


if __name__ == "__main__":
    main()
