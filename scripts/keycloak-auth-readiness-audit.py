#!/usr/bin/env python3
"""Read-only, privacy-preserving Keycloak account readiness inventory.

Never prints usernames, emails, credential values, tokens, or user IDs.
"""
import csv
import hashlib
import os
import sys
from collections import Counter
from urllib.parse import quote

import requests

BASE = os.environ["KEYCLOAK_BASE_URL"].rstrip("/")
REALM = os.environ.get("KEYCLOAK_REALM", "shopnoltd")
CLIENT_ID = os.environ["KEYCLOAK_ADMIN_CLIENT_ID"]
CLIENT_SECRET = os.environ["KEYCLOAK_ADMIN_CLIENT_SECRET"]
OUT = os.environ.get("REPORT_PATH", "auth-readiness.csv")
TIMEOUT = 20
session = requests.Session()
session.headers["Accept"] = "application/json"

def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)

try:
    response = session.post(
        f"{BASE}/realms/{quote(REALM, safe='')}/protocol/openid-connect/token",
        data={"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        fail(f"Could not obtain service-account token (HTTP {response.status_code}); verify the client and service-account roles.")
    token = response.json().get("access_token")
    if not token:
        fail("Token response did not contain an access token.")
    session.headers["Authorization"] = f"Bearer {token}"
    admin = f"{BASE}/admin/realms/{quote(REALM, safe='')}"
    users = []
    first = 0
    while True:
        r = session.get(f"{admin}/users", params={"first": first, "max": 100}, timeout=TIMEOUT)
        if r.status_code != 200:
            fail(f"Could not list realm users (HTTP {r.status_code}); grant least-privilege query/view user permissions.")
        batch = r.json()
        if not isinstance(batch, list):
            fail("Unexpected users response format.")
        users.extend(batch)
        if len(batch) < 100:
            break
        first += len(batch)

    counts = Counter()
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "account_ref", "enabled", "has_password", "has_otp",
            "has_federated_identity", "required_action_categories", "readiness"
        ])
        writer.writeheader()
        for user in users:
            uid = str(user.get("id") or "")
            if not uid:
                fail("A user record had no ID; refusing to produce an incomplete report.")
            account_ref = hashlib.sha256(uid.encode()).hexdigest()[:12]
            cr = session.get(f"{admin}/users/{quote(uid, safe='')}/credentials", timeout=TIMEOUT)
            if cr.status_code != 200:
                fail(f"Credential metadata unavailable for account ref {account_ref} (HTTP {cr.status_code}); report not complete.")
            credentials = cr.json()
            if not isinstance(credentials, list):
                fail(f"Unexpected credential metadata for account ref {account_ref}.")
            types = {str(c.get("type", "")).lower() for c in credentials}
            has_password = "password" in types
            has_otp = bool(types & {"otp", "totp"})
            fr = session.get(f"{admin}/users/{quote(uid, safe='')}/federated-identity", timeout=TIMEOUT)
            if fr.status_code != 200:
                fail(f"Federated identity metadata unavailable for account ref {account_ref} (HTTP {fr.status_code}); report not complete.")
            federated = bool(fr.json())
            actions = user.get("requiredActions") or []
            action_categories = []
            if "UPDATE_PASSWORD" in actions:
                action_categories.append("PASSWORD_SETUP_REQUIRED")
            if "CONFIGURE_TOTP" in actions:
                action_categories.append("MFA_SETUP_REQUIRED")
            if "VERIFY_EMAIL" in actions:
                action_categories.append("EMAIL_VERIFICATION_REQUIRED")
            if not user.get("enabled", False):
                readiness = "BLOCKED_DISABLED"
            elif has_password and "UPDATE_PASSWORD" not in actions:
                readiness = "PASSWORD_LOGIN_CANDIDATE"
            elif federated:
                readiness = "SOCIAL_LOGIN_CANDIDATE"
            elif "UPDATE_PASSWORD" in actions or not has_password:
                readiness = "PASSWORD_SETUP_REQUIRED"
            else:
                readiness = "REVIEW_REQUIRED"
            counts[readiness] += 1
            writer.writerow({
                "account_ref": account_ref,
                "enabled": bool(user.get("enabled", False)),
                "has_password": has_password,
                "has_otp": has_otp,
                "has_federated_identity": federated,
                "required_action_categories": ";".join(action_categories) or "none",
                "readiness": readiness,
            })
    print(f"Completed read-only inventory: {len(users)} accounts.")
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    print(f"Privacy-preserving CSV written to {OUT}; no usernames, emails, passwords, tokens, or raw user IDs are included.")
except requests.RequestException as exc:
    fail(f"Network request failed ({type(exc).__name__}); no response body or credentials logged.")
