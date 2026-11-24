#!/usr/bin/env python3
# Runtime OIDC client reconciliation is performed by the dedicated Keycloak sync workflow.

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://keycloak.shopno-identity.svc.cluster.local").rstrip("/")
REALM = os.environ.get("KEYCLOAK_REALM", "shopnoltd")
ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN_USER", "shopnoltd-admin")
ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD")

CLIENT_IDS = ["shopnoltd-web", "web-portal"]

REQUIRED_REDIRECT_URIS = [
    "https://mail-api.shopnoltd.dpdns.org/docs/oauth2-redirect",
    "http://localhost:5173/callback",
    "https://shopnoltd.dpdns.org/callback",
    "https://web-portal.shopnoltd.dpdns.org/callback",
    "https://files.shopnoltd.dpdns.org/callback",
    "https://shopnoltd.dpdns.org/android-cloud/callback",
    "https://admin-portal.shopnoltd.dpdns.org/callback",
    "https://devices.shopnoltd.dpdns.org/",
    "https://devices.shopnoltd.dpdns.org/callback",
    "https://device.shopnoltd.dpdns.org/",
    "https://device.shopnoltd.dpdns.org/callback",
    "https://android.shopnoltd.dpdns.org/",
    "https://android.shopnoltd.dpdns.org/callback",
    "shopnoltdcollect://oauth/callback",
]

REQUIRED_WEB_ORIGINS = [
    "https://mail-api.shopnoltd.dpdns.org",
    "http://localhost:5173",
    "https://shopnoltd.dpdns.org",
    "https://web-portal.shopnoltd.dpdns.org",
    "https://files.shopnoltd.dpdns.org",
    "https://admin-portal.shopnoltd.dpdns.org",
    "https://devices.shopnoltd.dpdns.org",
    "https://device.shopnoltd.dpdns.org",
    "https://android.shopnoltd.dpdns.org",
]

WEB_PORTAL_REDIRECT_URIS = [
    "https://shopnoltd.dpdns.org/*",
    "https://shopnoltd.dpdns.org/callback",
    "https://web-portal.shopnoltd.dpdns.org/*",
    "https://web-portal.shopnoltd.dpdns.org/callback",
    "https://billing.shopnoltd.dpdns.org/*",
    "https://billing.shopnoltd.dpdns.org/callback",
    "https://payment.shopnoltd.dpdns.org/*",
    "https://payment.shopnoltd.dpdns.org/callback",
    "https://exchange.shopnoltd.dpdns.org/*",
    "https://exchange.shopnoltd.dpdns.org/callback",
    "https://admin.shopnoltd.dpdns.org/*",
    "https://admin.shopnoltd.dpdns.org/callback",
    "https://support.shopnoltd.dpdns.org/*",
    "https://support.shopnoltd.dpdns.org/callback",
]

WEB_PORTAL_WEB_ORIGINS = [
    "https://shopnoltd.dpdns.org",
    "https://web-portal.shopnoltd.dpdns.org",
    "https://billing.shopnoltd.dpdns.org",
    "https://payment.shopnoltd.dpdns.org",
    "https://exchange.shopnoltd.dpdns.org",
    "https://admin.shopnoltd.dpdns.org",
    "https://support.shopnoltd.dpdns.org",
]

CLIENT_CONFIG = {
    "shopnoltd-web": {"redirect_uris": REQUIRED_REDIRECT_URIS, "web_origins": REQUIRED_WEB_ORIGINS},
    "web-portal": {"redirect_uris": WEB_PORTAL_REDIRECT_URIS, "web_origins": WEB_PORTAL_WEB_ORIGINS},
}
POST_LOGOUT_REDIRECT_URIS = {
    "shopnoltd-web": "https://shopnoltd.dpdns.org/*",
    "web-portal": "https://web-portal.shopnoltd.dpdns.org/*",
}

API_AUDIENCE_MAPPER_NAME = "api-service-audience"
API_AUDIENCE_REPAIR_MAPPER_NAME = "api-service-audience-repaired"
AI_AUDIENCE_MAPPER_NAME = "ai-platform-audience"
AI_AUDIENCE_REPAIR_MAPPER_NAME = "ai-platform-audience-repaired"
STORAGE_AUDIENCE_MAPPER_NAME = "storage-service-audience"
STORAGE_AUDIENCE_REPAIR_MAPPER_NAME = "storage-service-audience-repaired"
MAIL_AUDIENCE_MAPPER_NAME = "mail-service-audience"
MAIL_AUDIENCE_REPAIR_MAPPER_NAME = "mail-service-audience-repaired"


SOCIAL_PROVIDERS = {
    "google": {
        "providerId": "google",
        "clientIdEnv": "GOOGLE_CLIENT_ID",
        "clientSecretEnv": "GOOGLE_CLIENT_SECRET",
        "scope": "openid profile email",
    },
    "facebook": {
        "providerId": "facebook",
        "clientIdEnv": "FACEBOOK_LOGIN_APP_ID",
        "clientSecretEnv": "FACEBOOK_LOGIN_APP_SECRET",
        "scope": "email public_profile",
        # Meta's Facebook profile response exposes an email field but does not
        # provide a standard email_verified claim for Keycloak to validate.
        "trustEmail": False,
    },
    "github": {
        "providerId": "github",
        "clientIdEnv": "GITHUB_CLIENT_ID",
        "clientSecretEnv": "GITHUB_CLIENT_SECRET",
        "scope": "user:email read:user",
        # The Keycloak GitHub provider imports the primary email but not its
        # verified flag, so require Shopnoltd-side verification.
        "trustEmail": False,
    },
}


def request(method, path, token=None, body=None, form=False):
    data = None
    if body is not None:
        data = urllib.parse.urlencode(body).encode() if form else json.dumps(body).encode()
    req = urllib.request.Request(f"{KEYCLOAK_URL}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/x-www-form-urlencoded" if form else "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        print(f"[WARN] Keycloak request {method} {path} failed: {type(reason).__name__}: {reason}", file=sys.stderr, flush=True)
        return None, None


def get_admin_token():
    if not ADMIN_PASSWORD:
        raise RuntimeError("KEYCLOAK_ADMIN_PASSWORD is not set")
    code, payload = request(
        "POST",
        "/realms/master/protocol/openid-connect/token",
        body={"grant_type": "password", "client_id": "admin-cli", "username": ADMIN_USER, "password": ADMIN_PASSWORD},
        form=True,
    )
    if code != 200 or not isinstance(payload, dict) or not payload.get("access_token"):
        raise RuntimeError(f"Keycloak admin authentication failed (HTTP {code})")
    return payload["access_token"]


def sync_audience_mapper(token, client_uuid, *, canonical_name, repair_name, audience):
    code, mappers = request("GET", f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models", token=token)
    if code != 200 or not isinstance(mappers, list):
        raise RuntimeError(f"Unable to query Keycloak protocol mappers (HTTP {code})")
    audience_mappers = [m for m in mappers if m.get("name") in {canonical_name, repair_name} and m.get("protocol") == "openid-connect" and m.get("protocolMapper") == "oidc-audience-mapper"]
    audience_mapper = next((m for m in audience_mappers if m.get("name") == canonical_name and m.get("id")), None)
    if audience_mapper is None:
        audience_mapper = next((m for m in audience_mappers if m.get("id")), None)
    mapper_payload = {"protocol": "openid-connect", "protocolMapper": "oidc-audience-mapper", "config": {"included.custom.audience": audience, "included.client.audience": "", "id.token.claim": "false", "access.token.claim": "true", "access.tokenResponse.claim": "false"}}
    if audience_mapper:
        mapper_id = audience_mapper["id"]
        mapper_payload["id"] = mapper_id
        mapper_payload["name"] = audience_mapper["name"]
        code, _ = request("PUT", f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models/{mapper_id}", token=token, body=mapper_payload)
        if code != 204:
            raise RuntimeError(f"Unable to update {audience} audience mapper (HTTP {code})")
        if audience_mapper["name"] == repair_name:
            print(f"[OK] updated repaired {audience} audience mapper (malformed canonical mapper ignored)")
        else:
            print(f"[OK] updated {audience} audience mapper")
    else:
        malformed_canonical = any(m.get("name") == canonical_name and not m.get("id") for m in audience_mappers)
        mapper_payload["name"] = repair_name if malformed_canonical else canonical_name
        code, _ = request("POST", f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models", token=token, body=mapper_payload)
        if code != 201:
            raise RuntimeError(f"Unable to create {audience} audience mapper (HTTP {code})")
        if malformed_canonical:
            print(f"[OK] created repaired {audience} audience mapper; malformed canonical mapper was left untouched")
        else:
            print(f"[OK] created {audience} audience mapper")


def sync_api_audience_mapper(token, client_uuid):
    sync_audience_mapper(token, client_uuid, canonical_name=API_AUDIENCE_MAPPER_NAME, repair_name=API_AUDIENCE_REPAIR_MAPPER_NAME, audience="api-service")


def sync_ai_audience_mapper(token, client_uuid):
    sync_audience_mapper(token, client_uuid, canonical_name=AI_AUDIENCE_MAPPER_NAME, repair_name=AI_AUDIENCE_REPAIR_MAPPER_NAME, audience="ai-platform")


def sync_storage_audience_mapper(token, client_uuid):
    sync_audience_mapper(token, client_uuid, canonical_name=STORAGE_AUDIENCE_MAPPER_NAME, repair_name=STORAGE_AUDIENCE_REPAIR_MAPPER_NAME, audience="storage-service")


def sync_mail_audience_mapper(token, client_uuid):
    # Preserve the Mail API audience and its existing authorization checks.
    sync_audience_mapper(token, client_uuid, canonical_name=MAIL_AUDIENCE_MAPPER_NAME, repair_name=MAIL_AUDIENCE_REPAIR_MAPPER_NAME, audience="mail-service")


def sync_client(token, client_id):
    config = CLIENT_CONFIG[client_id]
    required_redirect_uris = config["redirect_uris"]
    required_web_origins = config["web_origins"]
    query = urllib.parse.urlencode({"clientId": client_id})
    code, clients = request("GET", f"/admin/realms/{REALM}/clients?{query}", token=token)
    if code != 200 or not isinstance(clients, list):
        raise RuntimeError(f"Unable to query Keycloak client (HTTP {code})")
    if clients:
        client = clients[0]
        client_uuid = client["id"]
        client["redirectUris"] = sorted(set((client.get("redirectUris") or []) + required_redirect_uris))
        client["webOrigins"] = sorted(set((client.get("webOrigins") or []) + required_web_origins))
        # Explicitly reconcile existing clients created by older manifests.\n        client["directAccessGrantsEnabled"] = False
        attributes = client.get("attributes") or {}
        attributes["pkce.code.challenge.method"] = "S256"
        attributes["post.logout.redirect.uris"] = POST_LOGOUT_REDIRECT_URIS[client_id]
        client["attributes"] = attributes
        code, _ = request("PUT", f"/admin/realms/{REALM}/clients/{client_uuid}", token=token, body=client)
        if code != 204:
            raise RuntimeError(f"Unable to update Keycloak client (HTTP {code})")
        sync_api_audience_mapper(token, client_uuid)
        sync_ai_audience_mapper(token, client_uuid)
        sync_storage_audience_mapper(token, client_uuid)
        sync_mail_audience_mapper(token, client_uuid)
        print(f"[OK] synchronized {client_id} with api-service, ai-platform, storage-service and mail-service JWT audiences")
    else:
        payload = {"clientId": client_id, "publicClient": True, "protocol": "openid-connect", "standardFlowEnabled": True, "directAccessGrantsEnabled": False, "redirectUris": required_redirect_uris, "webOrigins": required_web_origins, "attributes": {"pkce.code.challenge.method": "S256", "post.logout.redirect.uris": POST_LOGOUT_REDIRECT_URIS[client_id]}}
        code, _ = request("POST", f"/admin/realms/{REALM}/clients", token=token, body=payload)
        if code != 201:
            raise RuntimeError(f"Unable to create Keycloak client (HTTP {code})")
        code, clients = request("GET", f"/admin/realms/{REALM}/clients?{query}", token=token)
        if code != 200 or not isinstance(clients, list) or not clients:
            raise RuntimeError(f"Unable to re-query newly-created Keycloak client (HTTP {code})")
        client_uuid = clients[0]["id"]
        sync_api_audience_mapper(token, client_uuid)
        sync_ai_audience_mapper(token, client_uuid)
        sync_storage_audience_mapper(token, client_uuid)
        sync_mail_audience_mapper(token, client_uuid)
        print(f"[OK] created {client_id} client")
        print(f"[OK] synchronized {client_id} with api-service, ai-platform, storage-service and mail-service JWT audiences")



    # Read the persisted client back from Keycloak so a successful PUT is not
    # mistaken for a completed redirect-URI repair.
    verify_code, verified_client = request("GET", f"/admin/realms/{REALM}/clients/{client_uuid}", token=token)
    if verify_code != 200 or not isinstance(verified_client, dict):
        raise RuntimeError(f"Unable to verify persisted Keycloak client {client_id} (HTTP {verify_code})")
    missing_redirects = sorted(set(required_redirect_uris) - set(verified_client.get("redirectUris") or []))
    missing_origins = sorted(set(required_web_origins) - set(verified_client.get("webOrigins") or []))
    if missing_redirects or missing_origins:
        raise RuntimeError(
            f"Keycloak client {client_id} is missing redirect URIs {missing_redirects} "
            f"or web origins {missing_origins}"
        )
    print(f"[OK] verified persisted redirect URIs and web origins for {client_id}")



def sync_realm_smtp(token):
    """Configure Keycloak password-recovery email through Shopnoltd's existing Brevo relay."""
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_port = os.environ.get("SMTP_PORT", "").strip()
    smtp_user = os.environ.get("SMTP_USERNAME", "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_ENVELOPE_FROM", "").strip()
    if not all((smtp_host, smtp_port, smtp_user, smtp_password, sender)):
        raise RuntimeError("SMTP relay configuration is incomplete; refusing to enable password recovery without mail delivery settings")

    expected = {
        "host": smtp_host,
        "port": smtp_port,
        "from": sender,
        "envelopeFrom": sender,
        "auth": "true",
        "user": smtp_user,
        "password": smtp_password,
        "starttls": "true",
        "ssl": "false",
    }
    code, realm = request("GET", f"/admin/realms/{REALM}", token=token)
    if code != 200 or not isinstance(realm, dict):
        raise RuntimeError(f"Unable to read Keycloak realm settings before SMTP reconciliation (HTTP {code})")

    # Preserve all existing realm settings; change only password-recovery enablement
    # and the SMTP transport configuration required to deliver reset/action emails.
    realm["resetPasswordAllowed"] = True
    realm["smtpServer"] = expected
    code, _ = request("PUT", f"/admin/realms/{REALM}", token=token, body=realm)
    if code not in (200, 204):
        raise RuntimeError(f"Unable to configure Keycloak password-recovery SMTP (HTTP {code})")

    verify_code, verified_realm = request("GET", f"/admin/realms/{REALM}", token=token)
    if verify_code != 200 or not isinstance(verified_realm, dict):
        raise RuntimeError(f"Unable to verify persisted Keycloak SMTP settings (HTTP {verify_code})")
    persisted = verified_realm.get("smtpServer") or {}
    public_fields = ("host", "port", "from", "envelopeFrom", "auth", "user", "starttls", "ssl")
    mismatches = [field for field in public_fields if str(persisted.get(field, "")) != expected[field]]
    if mismatches or not verified_realm.get("resetPasswordAllowed"):
        raise RuntimeError(
            "Keycloak password-recovery SMTP settings did not persist as expected "
            f"(mismatched fields: {mismatches}, reset_password_allowed={bool(verified_realm.get('resetPasswordAllowed'))})"
        )
    print("[OK] verified persisted Keycloak password-recovery SMTP settings (relay, sender, authentication, STARTTLS)")
    print("[OK] Keycloak Forgot Password is enabled; no user accounts or credentials were changed")


LOGIN_FIRST_BROKER_FLOW = "shopnoltd social login existing users only"
LOGIN_ONLY_DISABLED_AUTHENTICATORS = {
    "idp-create-user-if-unique",
    "idp-confirm-link",
    "idp-username-password-form",
}
LOGIN_ONLY_REQUIRED_AUTHENTICATORS = {"idp-email-verification"}


def ensure_login_first_broker_flow(token):
    """Require email ownership verification for existing users without a Shopnoltd password prompt."""
    code, flows = request("GET", f"/admin/realms/{REALM}/authentication/flows", token=token)
    if code != 200 or not isinstance(flows, list):
        raise RuntimeError(f"Unable to inspect Keycloak authentication flows (HTTP {code})")

    if not any(flow.get("alias") == LOGIN_FIRST_BROKER_FLOW for flow in flows):
        source = urllib.parse.quote("first broker login", safe="")
        code, _ = request(
            "POST",
            f"/admin/realms/{REALM}/authentication/flows/{source}/copy",
            token=token,
            body={"newName": LOGIN_FIRST_BROKER_FLOW},
        )
        if code not in (201, 409):
            raise RuntimeError(f"Unable to create social Login first-broker flow (HTTP {code})")

    code, flows = request("GET", f"/admin/realms/{REALM}/authentication/flows", token=token)
    if code != 200 or not isinstance(flows, list):
        raise RuntimeError(f"Unable to verify Keycloak authentication flows (HTTP {code})")
    if not any(flow.get("alias") == LOGIN_FIRST_BROKER_FLOW for flow in flows):
        raise RuntimeError("Social Login first-broker flow was not created")

    encoded_alias = urllib.parse.quote(LOGIN_FIRST_BROKER_FLOW, safe="")
    code, executions = request(
        "GET",
        f"/admin/realms/{REALM}/authentication/flows/{encoded_alias}/executions",
        token=token,
    )
    if code != 200 or not isinstance(executions, list):
        raise RuntimeError(f"Unable to inspect social Login first-broker flow (HTTP {code})")

    # Keycloak's executions endpoint returns nested subflow executions recursively.
    # Existing-account ownership is proven by Keycloak's email action link, not by
    # re-entering the Shopnoltd password. Never allow account creation in this flow.
    required_policies = {
        **{provider: "DISABLED" for provider in LOGIN_ONLY_DISABLED_AUTHENTICATORS},
        **{provider: "REQUIRED" for provider in LOGIN_ONLY_REQUIRED_AUTHENTICATORS},
    }
    found_authenticators = set()
    updates = []
    for execution in executions:
        provider_id = execution.get("providerId")
        if provider_id in required_policies:
            found_authenticators.add(provider_id)
            expected_requirement = required_policies[provider_id]
            if execution.get("requirement") != expected_requirement:
                updated = dict(execution)
                updated["requirement"] = expected_requirement
                updates.append(updated)

    missing = set(required_policies) - found_authenticators
    if missing:
        raise RuntimeError(
            "Keycloak Login-only flow is missing required email-verification policy executions: "
            + ", ".join(sorted(missing))
        )

    # Keycloak expects one AuthenticationExecutionInfoRepresentation per PUT,
    # not the complete list returned by GET.
    for execution in updates:
        code, _ = request(
            "PUT",
            f"/admin/realms/{REALM}/authentication/flows/{encoded_alias}/executions",
            token=token,
            body=execution,
        )
        if code not in (200, 204):
            raise RuntimeError(
                "Unable to enforce Login-only policy for execution "
                f"'{execution.get('id')}' (HTTP {code})"
            )

    print("[OK] social Login flow requires email verification and disables password re-authentication and automatic account creation")

def sync_social_provider(token, alias, provider, first_broker_flow_alias="first broker login"):
    client_id = os.environ.get(provider["clientIdEnv"], "").strip()
    client_secret = os.environ.get(provider["clientSecretEnv"], "").strip()
    if not client_id or not client_secret:
        return False
    payload = {
        "alias": alias,
        "providerId": provider["providerId"],
        "enabled": True,
        # Keep signup-only aliases available to explicit kc_idp_hint flows,
        # but do not render them as duplicate buttons on the normal login page.
        "hideOnLogin": alias.endswith("-signup"),
        "trustEmail": provider.get("trustEmail", True),
        "storeToken": False,
        "firstBrokerLoginFlowAlias": first_broker_flow_alias,
        "config": {
            "clientId": client_id,
            "clientSecret": client_secret,
            "defaultScope": provider["scope"],
        },
    }
    code, _ = request("GET", f"/admin/realms/{REALM}/identity-provider/instances/{alias}", token=token)
    if code == 200:
        code, _ = request("PUT", f"/admin/realms/{REALM}/identity-provider/instances/{alias}", token=token, body=payload)
        if code not in (200, 204):
            raise RuntimeError(f"Unable to update {alias} identity provider (HTTP {code})")
        print(f"[OK] synchronized {alias} identity provider")
    else:
        code, _ = request("POST", f"/admin/realms/{REALM}/identity-provider/instances", token=token, body=payload)
        if code != 201:
            raise RuntimeError(f"Unable to create {alias} identity provider (HTTP {code})")
        print(f"[OK] created {alias} identity provider")
    return True


def sync_social_providers(token):
    configured = [
        (alias, provider)
        for alias, provider in SOCIAL_PROVIDERS.items()
        if os.environ.get(provider["clientIdEnv"], "").strip()
        and os.environ.get(provider["clientSecretEnv"], "").strip()
    ]
    if not configured:
        print("[INFO] no social provider credentials configured; leaving Keycloak social providers unchanged")
        return

    ensure_login_first_broker_flow(token)
    synchronized = []
    for alias, provider in configured:
        if sync_social_provider(token, alias, provider, LOGIN_FIRST_BROKER_FLOW):
            synchronized.append(alias)
        signup_alias = "{}-signup".format(alias)
        if sync_social_provider(token, signup_alias, provider):
            synchronized.append(signup_alias)
    print("[OK] social Login and direct Signup identity providers synchronized: " + ", ".join(synchronized))


def main():
    last_error = None
    max_attempts = 8
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"[INFO] Keycloak client sync attempt {attempt}/{max_attempts}", flush=True)
            token = get_admin_token()
            sync_realm_smtp(token)
            for client_id in CLIENT_IDS:
                sync_client(token, client_id)
            sync_social_providers(token)
            print("[OK] Keycloak client synchronization completed", flush=True)
            return
        except Exception as exc:
            last_error = exc
            print(f"[WARN] Keycloak client sync attempt {attempt}/{max_attempts} failed: {exc}", file=sys.stderr, flush=True)
            if attempt < max_attempts:
                time.sleep(3)
    print(f"[FAIL] Keycloak client sync exhausted {max_attempts} attempts: {last_error}", file=sys.stderr, flush=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
