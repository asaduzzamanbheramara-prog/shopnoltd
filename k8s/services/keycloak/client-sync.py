#!/usr/bin/env python3

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KEYCLOAK_URL = os.environ.get(
    "KEYCLOAK_URL",
    "http://keycloak.shopno-identity.svc.cluster.local",
).rstrip("/")

REALM = os.environ.get("KEYCLOAK_REALM", "shopnoltd")
ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD")

CLIENT_ID = "shopnoltd-web"

REQUIRED_REDIRECT_URIS = [
    "http://localhost:5173/callback",
    "https://shopnoltd.dpdns.org/callback",
    "https://devices.shopnoltd.dpdns.org/",
    "https://devices.shopnoltd.dpdns.org/callback",
]

REQUIRED_WEB_ORIGINS = [
    "http://localhost:5173",
    "https://shopnoltd.dpdns.org",
    "https://devices.shopnoltd.dpdns.org",
]


API_AUDIENCE_MAPPER_NAME = "api-service-audience"
API_AUDIENCE_REPAIR_MAPPER_NAME = "api-service-audience-repaired"


def request(method, path, token=None, body=None, form=False):
    data = None

    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode()
        else:
            data = json.dumps(body).encode()

    req = urllib.request.Request(
        f"{KEYCLOAK_URL}{path}",
        data=data,
        method=method,
    )

    req.add_header(
        "Content-Type",
        "application/x-www-form-urlencoded"
        if form
        else "application/json",
    )

    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None

    except urllib.error.HTTPError as exc:
        return exc.code, None

    except Exception:
        return None, None


def get_admin_token():
    if not ADMIN_PASSWORD:
        raise RuntimeError("KEYCLOAK_ADMIN_PASSWORD is not set")

    code, payload = request(
        "POST",
        "/realms/master/protocol/openid-connect/token",
        body={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD,
        },
        form=True,
    )

    if (
        code != 200
        or not isinstance(payload, dict)
        or not payload.get("access_token")
    ):
        raise RuntimeError(
            f"Keycloak admin authentication failed (HTTP {code})"
        )

    return payload["access_token"]


def sync_client(token):
    query = urllib.parse.urlencode({"clientId": CLIENT_ID})

    code, clients = request(
        "GET",
        f"/admin/realms/{REALM}/clients?{query}",
        token=token,
    )

    if code != 200 or not isinstance(clients, list):
        raise RuntimeError(
            f"Unable to query Keycloak client (HTTP {code})"
        )

    if clients:
        client = clients[0]
        client_uuid = client["id"]

        client["redirectUris"] = sorted(
            set(
                (client.get("redirectUris") or [])
                + REQUIRED_REDIRECT_URIS
            )
        )

        client["webOrigins"] = sorted(
            set(
                (client.get("webOrigins") or [])
                + REQUIRED_WEB_ORIGINS
            )
        )

        attributes = client.get("attributes") or {}
        attributes["pkce.code.challenge.method"] = "S256"
        client["attributes"] = attributes

        code, _ = request(
            "PUT",
            f"/admin/realms/{REALM}/clients/{client_uuid}",
            token=token,
            body=client,
        )

        if code != 204:
            raise RuntimeError(
                f"Unable to update Keycloak client (HTTP {code})"
            )

        # The client protocol-mapper endpoint does not require a `client`
        # query parameter. Use the canonical REST endpoint directly.
        code, mappers = request(
            "GET",
            f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models",
            token=token,
        )

        if code != 200 or not isinstance(mappers, list):
            raise RuntimeError(
                f"Unable to query Keycloak protocol mappers (HTTP {code})"
            )

        audience_mappers = [
            m for m in mappers
            if m.get("name") in {
                API_AUDIENCE_MAPPER_NAME,
                API_AUDIENCE_REPAIR_MAPPER_NAME,
            }
            and m.get("protocol") == "openid-connect"
            and m.get("protocolMapper") == "oidc-audience-mapper"
        ]

        # Prefer the canonical mapper when it has a real server-generated ID.
        # A malformed mapper with id=null must never be sent to the update API.
        audience_mapper = next(
            (
                m for m in audience_mappers
                if m.get("name") == API_AUDIENCE_MAPPER_NAME
                and m.get("id")
            ),
            None,
        )

        if audience_mapper is None:
            audience_mapper = next(
                (
                    m for m in audience_mappers
                    if m.get("id")
                ),
                None,
            )

        mapper_payload = {
            "protocol": "openid-connect",
            "protocolMapper": "oidc-audience-mapper",
            "config": {
                "included.client.audience": "api-service",
                "id.token.claim": "false",
                "access.token.claim": "true",
                "access.tokenResponse.claim": "false",
            },
        }

        if audience_mapper:
            mapper_payload["name"] = audience_mapper["name"]
            mapper_id = audience_mapper["id"]

            code, _ = request(
                "PUT",
                f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models/{mapper_id}",
                token=token,
                body=mapper_payload,
            )

            if code != 204:
                raise RuntimeError(
                    f"Unable to update api-service audience mapper (HTTP {code})"
                )

            if audience_mapper["name"] == API_AUDIENCE_REPAIR_MAPPER_NAME:
                print(
                    "[OK] updated repaired api-service audience mapper "
                    "(malformed canonical mapper ignored)"
                )
            else:
                print("[OK] updated api-service audience mapper")
        else:
            # If the canonical mapper exists but has id=null, Keycloak's
            # update endpoint cannot address it. Do not PUT /null and do not
            # repeatedly attempt to create another mapper with the same name.
            malformed_canonical = any(
                m.get("name") == API_AUDIENCE_MAPPER_NAME
                and not m.get("id")
                for m in audience_mappers
            )

            mapper_payload["name"] = (
                API_AUDIENCE_REPAIR_MAPPER_NAME
                if malformed_canonical
                else API_AUDIENCE_MAPPER_NAME
            )

            code, _ = request(
                "POST",
                f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models",
                token=token,
                body=mapper_payload,
            )

            if code != 201:
                raise RuntimeError(
                    f"Unable to create api-service audience mapper "
                    f"(HTTP {code})"
                )

            if malformed_canonical:
                print(
                    "[OK] created repaired api-service audience mapper; "
                    "malformed canonical mapper was left untouched"
                )
            else:
                print("[OK] created api-service audience mapper")

        print(
            "[OK] synchronized shopnoltd-web "
            "with api-service JWT audience"
        )

    else:
        payload = {
            "clientId": CLIENT_ID,
            "publicClient": True,
            "protocol": "openid-connect",
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": False,
            "redirectUris": REQUIRED_REDIRECT_URIS,
            "webOrigins": REQUIRED_WEB_ORIGINS,
            "attributes": {
                "pkce.code.challenge.method": "S256",
            },
        }

        code, _ = request(
            "POST",
            f"/admin/realms/{REALM}/clients",
            token=token,
            body=payload,
        )

        if code != 201:
            raise RuntimeError(
                f"Unable to create Keycloak client (HTTP {code})"
            )

        print("[OK] created shopnoltd-web client")


def main():
    last_error = None

    for _ in range(30):
        try:
            token = get_admin_token()
            sync_client(token)
            return

        except Exception as exc:
            last_error = exc
            time.sleep(5)

    print(
        f"[FAIL] Keycloak client sync: {last_error}",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
