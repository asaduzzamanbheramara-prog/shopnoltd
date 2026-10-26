#!/usr/bin/env python3
"""
Create the platform's 3-tier realm roles in Keycloak: platform_admin,
tenant_owner, customer -- and a client scope mapper so realm roles show up
in the JWT as a flat "roles" claim (matching what app/core/security.py in
oauth-service already expects).

Usage:
    export KEYCLOAK_URL=https://auth.shopnoltd.dpdns.org
    export KEYCLOAK_REALM=shopnoltd
    export KEYCLOAK_ADMIN_USER=admin
    export KEYCLOAK_ADMIN_PASSWORD='...'
    python3 scripts/setup_rbac_roles.py
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "https://auth.shopnoltd.dpdns.org").rstrip("/")
REALM = os.environ.get("KEYCLOAK_REALM", "shopnoltd")
ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD")

ROLES = {
    "platform_admin": "Full access across all tenants -- Shopnoltd staff only.",
    "tenant_owner": "Manages one tenant: its customers, theme, texts, plugins.",
    "customer": "End customer -- can self-service their own profile only.",
}


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
    req = urllib.request.Request(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token", data=body, method="POST"
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"Failed to get admin token ({e.code}): {e.read().decode(errors='replace')}")


def main():
    token = get_admin_token()

    for name, description in ROLES.items():
        code, existing = http("GET", f"/admin/realms/{REALM}/roles/{name}", token)
        if code == 200:
            print(f"[SKIP] role '{name}' already exists")
            continue
        code, resp = http(
            "POST",
            f"/admin/realms/{REALM}/roles",
            token,
            {"name": name, "description": description},
        )
        print(
            f"[{'OK' if code in (201,) else 'FAIL'}] create role '{name}' (HTTP {code})"
            + ("" if code == 201 else f": {resp}")
        )

    # Ensure realm roles are exposed in the token as a flat "roles" claim.
    # Keycloak's built-in "realm roles" client scope maps to "realm_access.roles"
    # by default; app/core/security.py reads a top-level "roles" claim, so add
    # a dedicated user-realm-role mapper named "roles" at the realm-roles scope.
    code, scopes = http("GET", f"/admin/realms/{REALM}/client-scopes", token)
    realm_roles_scope = next((s for s in (scopes or []) if s.get("name") == "roles"), None)
    if not realm_roles_scope:
        print(
            "[WARN] couldn't find the built-in 'roles' client scope -- add the "
            "'roles' claim mapper manually in the Keycloak admin console "
            "(Client Scopes -> roles -> Mappers -> Add mapper -> User Realm Role, "
            "Token Claim Name = roles, Multivalued = On)."
        )
        return
    scope_id = realm_roles_scope["id"]
    code, mappers = http(
        "GET", f"/admin/realms/{REALM}/client-scopes/{scope_id}/protocol-mappers/models", token
    )
    if any(m.get("name") == "flat-roles" for m in (mappers or [])):
        print("[SKIP] 'flat-roles' mapper already exists")
    else:
        mapper = {
            "name": "flat-roles",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-realm-role-mapper",
            "config": {
                "claim.name": "roles",
                "jsonType.label": "String",
                "multivalued": "true",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "userinfo.token.claim": "true",
            },
        }
        code, resp = http(
            "POST",
            f"/admin/realms/{REALM}/client-scopes/{scope_id}/protocol-mappers/models",
            token,
            mapper,
        )
        print(
            f"[{'OK' if code in (201,) else 'FAIL'}] create 'flat-roles' mapper (HTTP {code})"
            + ("" if code == 201 else f": {resp}")
        )

    # Expose the tenant_id user attribute as a top-level JWT claim. The
    # dashboard and tenant-scoped APIs read user.get("tenant_id"), so a role
    # alone is not enough to assign a tenant owner to a tenant.
    tenant_mapper = {
        "name": "tenant-id",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "config": {
            "user.attribute": "tenant_id",
            "claim.name": "tenant_id",
            "jsonType.label": "String",
            "multivalued": "false",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        },
    }
    if any(m.get("name") == "tenant-id" for m in (mappers or [])):
        print("[SKIP] 'tenant-id' mapper already exists")
    else:
        code, resp = http(
            "POST",
            f"/admin/realms/{REALM}/client-scopes/{scope_id}/protocol-mappers/models",
            token,
            tenant_mapper,
        )
        print(
            f"[{'OK' if code == 201 else 'FAIL'}] create 'tenant-id' mapper (HTTP {code})"
            + ("" if code == 201 else f": {resp}")
        )

    # Optional, explicit assignment for a dedicated test tenant-owner account.
    # This is intentionally opt-in; never guess a tenant ID or change users
    # unless both environment variables are provided by the operator.
    tenant_owner_username = os.environ.get("KEYCLOAK_TENANT_OWNER_USERNAME")
    tenant_id = os.environ.get("KEYCLOAK_TENANT_ID")
    if tenant_owner_username or tenant_id:
        if not tenant_owner_username or not tenant_id:
            sys.exit(
                "Set both KEYCLOAK_TENANT_OWNER_USERNAME and KEYCLOAK_TENANT_ID "
                "to assign a tenant; no user attributes were changed."
            )
        code, users = http(
            "GET",
            f"/admin/realms/{REALM}/users?username={urllib.parse.quote(tenant_owner_username)}&exact=true",
            token,
        )
        if code != 200 or not isinstance(users, list):
            sys.exit(f"Could not look up the requested tenant-owner account (HTTP {code}); no user attributes were changed.")
        matches = [u for u in users if u.get("username") == tenant_owner_username]
        if len(matches) != 1:
            sys.exit(
                f"Expected exactly one Keycloak user named {tenant_owner_username!r}; "
                f"found {len(matches)}. No user attributes were changed."
            )
        user = matches[0]
        attributes = user.get("attributes") or {}
        attributes["tenant_id"] = [tenant_id]
        code, resp = http(
            "PUT",
            f"/admin/realms/{REALM}/users/{user['id']}",
            token,
            {"attributes": attributes},
        )
        if code not in (200, 204):
            sys.exit(f"Failed to assign tenant_id to the selected user (HTTP {code}): {resp}")
        print(f"[OK] set tenant_id for the explicitly selected tenant-owner account {tenant_owner_username!r}")

    print("\nDone. Assign roles to users with:")
    print(
        "  PUT /admin/realms/{realm}/users/{user-id}/role-mappings/realm  "
        'body=[{"id":"<role-id>","name":"tenant_owner"}]'
    )
    print(
        "For tenant_owner/customer, also set a 'tenant_id' user attribute "
        "and add a matching user-attribute mapper (Token Claim Name = tenant_id) "
        "so it lands in the token the same way."
    )


if __name__ == "__main__":
    main()
