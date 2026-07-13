#!/usr/bin/env python3
"""
Register the 'web-portal' public client in Keycloak so Login.jsx/Register.jsx/
Callback.jsx (PKCE authorization-code flow, no client secret) actually work.

Usage:
    export KEYCLOAK_URL=https://auth.shopnoltd.dpdns.org
    export KEYCLOAK_REALM=shopnoltd
    export KEYCLOAK_ADMIN_USER=admin
    export KEYCLOAK_ADMIN_PASSWORD='...'
    export WEB_PORTAL_ORIGIN=https://web-portal.shopnoltd.dpdns.org
    python3 scripts/setup_web_portal_client.py
"""
import os
import sys
import json
import urllib.request
import urllib.error

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "https://auth.shopnoltd.dpdns.org").rstrip("/")
REALM = os.environ.get("KEYCLOAK_REALM", "shopnoltd")
ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD")
ORIGIN = os.environ.get("WEB_PORTAL_ORIGIN", "https://web-portal.shopnoltd.dpdns.org").rstrip("/")
CLIENT_ID = "web-portal"


def http(method, path, token=None, body=None):
    req = urllib.request.Request(
        f"{KEYCLOAK_URL}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
    )
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
        sys.exit("Set KEYCLOAK_ADMIN_PASSWORD before running this script.")
    body = f"grant_type=password&client_id=admin-cli&username={ADMIN_USER}&password={ADMIN_PASSWORD}".encode()
    req = urllib.request.Request(f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token", data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"Failed to get admin token ({e.code}): {e.read().decode(errors='replace')}")


def main():
    token = get_admin_token()
    code, clients = http("GET", f"/admin/realms/{REALM}/clients?clientId={CLIENT_ID}", token)
    payload = {
        "clientId": CLIENT_ID,
        "publicClient": True,          # no client secret -- PKCE handles proof of possession
        "protocol": "openid-connect",
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "redirectUris": [f"{ORIGIN}/callback", f"{ORIGIN}/*"],
        "webOrigins": [ORIGIN],
        "attributes": {
            "pkce.code.challenge.method": "S256",
            "post.logout.redirect.uris": f"{ORIGIN}/*",
        },
    }
    if clients:
        client_uuid = clients[0]["id"]
        code, resp = http("PUT", f"/admin/realms/{REALM}/clients/{client_uuid}", token, payload)
        print(f"[{'OK' if code == 204 else 'FAIL'}] updated existing '{CLIENT_ID}' client (HTTP {code})" + ("" if code == 204 else f": {resp}"))
    else:
        code, resp = http("POST", f"/admin/realms/{REALM}/clients", token, payload)
        print(f"[{'OK' if code == 201 else 'FAIL'}] created '{CLIENT_ID}' client (HTTP {code})" + ("" if code == 201 else f": {resp}"))

    if code not in (201, 204):
        sys.exit(1)
    print(f"\nRedirect URIs registered: {ORIGIN}/callback")
    print("If your web-portal build uses a different origin/domain, re-run with WEB_PORTAL_ORIGIN set to it.")


if __name__ == "__main__":
    main()
