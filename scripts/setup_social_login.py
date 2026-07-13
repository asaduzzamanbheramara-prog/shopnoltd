#!/usr/bin/env python3
"""
Register Google, Facebook, and GitHub as Keycloak Identity Providers.

Why this and not custom OAuth code in oauth-service:
Every service in this platform authenticates via Keycloak OIDC
(see docs/SERVICE_TOPOLOGY.md). Keycloak already has first-class support
for brokering Google/Facebook/GitHub logins ("Identity Providers"), so once
this is set up, ALL services get social login for free through the existing
Keycloak session -- no new auth code, no duplicate token logic, no new
attack surface in oauth-service.

Usage:
    export KEYCLOAK_URL=https://auth.shopnoltd.dpdns.org
    export KEYCLOAK_REALM=shopnoltd
    export KEYCLOAK_ADMIN_USER=admin
    export KEYCLOAK_ADMIN_PASSWORD=...            # the real bootstrap password
    python3 scripts/setup_social_login.py scripts/seed/social-login-secrets.local.yaml

Idempotent: re-running updates existing providers instead of failing.
"""
import os
import sys
import json
import yaml
import urllib.request
import urllib.error

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "https://auth.shopnoltd.dpdns.org").rstrip("/")
REALM = os.environ.get("KEYCLOAK_REALM", "shopnoltd")
ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD")


def http(method, path, token=None, body=None):
    url = f"{KEYCLOAK_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, (json.loads(raw) if raw else raw.decode(errors="replace"))


def get_admin_token():
    if not ADMIN_PASSWORD:
        sys.exit("Set KEYCLOAK_ADMIN_PASSWORD in your shell before running this script.")
    body = (
        f"grant_type=password&client_id=admin-cli"
        f"&username={ADMIN_USER}&password={ADMIN_PASSWORD}"
    ).encode()
    req = urllib.request.Request(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data=body,
        method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"Failed to get admin token ({e.code}): {e.read().decode(errors='replace')}")


def upsert_idp(token, alias, provider_id, config):
    status, existing = http("GET", f"/admin/realms/{REALM}/identity-provider/instances/{alias}", token)
    payload = {
        "alias": alias,
        "providerId": provider_id,
        "enabled": True,
        "trustEmail": True,
        "storeToken": False,
        "firstBrokerLoginFlowAlias": "first broker login",
        "config": config,
    }
    if status == 200:
        code, resp = http("PUT", f"/admin/realms/{REALM}/identity-provider/instances/{alias}", token, payload)
        action = "updated"
    else:
        code, resp = http("POST", f"/admin/realms/{REALM}/identity-provider/instances", token, payload)
        action = "created"
    ok = code in (200, 201, 204)
    print(f"[{'OK' if ok else 'FAIL'}] {alias} {action} (HTTP {code})" + ("" if ok else f": {resp}"))
    return ok


def main():
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <path-to-social-login-secrets.local.yaml>")
    with open(sys.argv[1]) as f:
        creds = yaml.safe_load(f)

    token = get_admin_token()
    results = []

    if creds.get("google", {}).get("client_id"):
        results.append(upsert_idp(token, "google", "google", {
            "clientId": creds["google"]["client_id"],
            "clientSecret": creds["google"]["client_secret"],
            "defaultScope": "openid profile email",
            "useJwksUrl": "true",
        }))

    if creds.get("facebook", {}).get("app_id"):
        results.append(upsert_idp(token, "facebook", "facebook", {
            "clientId": creds["facebook"]["app_id"],
            "clientSecret": creds["facebook"]["app_secret"],
            "defaultScope": "email public_profile",
        }))

    if creds.get("github", {}).get("client_id"):
        results.append(upsert_idp(token, "github", "github", {
            "clientId": creds["github"]["client_id"],
            "clientSecret": creds["github"]["client_secret"],
            "defaultScope": "user:email",
        }))

    if not all(results):
        sys.exit(1)
    print("\nDone. Add each provider's redirect URI to its developer console:")
    for alias in ("google", "facebook", "github"):
        print(f"  {alias}: {KEYCLOAK_URL}/realms/{REALM}/broker/{alias}/endpoint")


if __name__ == "__main__":
    main()
