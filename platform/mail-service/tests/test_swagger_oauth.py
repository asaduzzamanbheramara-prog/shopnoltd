"""OpenAPI contract tests for browser-based Mail API authorization."""

import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.main import app


def test_mail_api_openapi_uses_keycloak_authorization_code_flow():
    schema = app.openapi()
    security_schemes = schema["components"]["securitySchemes"]

    oauth_name, oauth_scheme = next(
        (name, value)
        for name, value in security_schemes.items()
        if value.get("type") == "oauth2"
    )

    flow = oauth_scheme["flows"]["authorizationCode"]
    assert flow["authorizationUrl"] == (
        "https://auth.shopnoltd.dpdns.org/realms/shopnoltd/"
        "protocol/openid-connect/auth"
    )
    assert flow["tokenUrl"] == (
        "https://auth.shopnoltd.dpdns.org/realms/shopnoltd/"
        "protocol/openid-connect/token"
    )
    assert {"openid", "profile", "email"}.issubset(flow["scopes"])

    for path, method in (
        ("/api/v1/mailboxes/mine", "get"),
        ("/api/v1/messages/send", "post"),
    ):
        requirements = schema["paths"][path][method]["security"]
        assert any(oauth_name in requirement for requirement in requirements)


def test_swagger_ui_uses_public_shopnoltd_pkce_client():
    oauth_config = getattr(app, "swagger_ui_init_oauth", None)
    assert oauth_config is not None
    assert oauth_config["clientId"] == "shopnoltd-web"
    assert oauth_config["usePkceWithAuthorizationCodeGrant"] is True
    assert oauth_config["scopes"] == "openid profile email"
