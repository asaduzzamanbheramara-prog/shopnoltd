#!/usr/bin/env python3
"""Static regression checks for Shopnoltd's browser OIDC contract.

These checks deliberately require no live credentials and never use the
Resource Owner Password Credentials (direct-access-grant) flow. Production
login must be verified separately with the Playwright smoke workflow.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    file = ROOT / path
    if not file.is_file():
        raise SystemExit(f"Missing required auth file: {path}")
    return file.read_text(encoding="utf-8")


login = read("platform/web-portal/src/pages/Login.jsx")
callback = read("platform/web-portal/src/pages/Callback.jsx")
config = read("platform/web-portal/src/config.js")
sync = read("k8s/services/keycloak/client-sync.py")
role_test = read("tests/browser-role/authenticated-production.spec.js")

checks = {
    "browser login uses PKCE S256": "code_challenge_method: 'S256'" in login,
    "browser login uses authorization-code flow": "response_type: 'code'" in login,
    "browser callback validates state": "returnedState !== expectedState" in callback,
    "browser callback exchanges code with verifier": "code_verifier: verifier" in callback,
    "default browser client is shopnoltd-web": "'shopnoltd-web'" in config,
    "existing clients do not enable direct access grants": 'client["directAccessGrantsEnabled"] = False' in sync,
    "new clients do not enable direct access grants": '"directAccessGrantsEnabled": False' in sync,
    "production smoke checks successful dashboard login": "pathname === '/dashboard'" in role_test,
    "production smoke checks live database inventory": "/api/v1/admin/database/live-catalog" in role_test,
    "production smoke checks non-admin denial": "normal user is denied the admin database route" in role_test,
}
failed = [name for name, passed in checks.items() if not passed]
for name, passed in checks.items():
    print(f"[{'PASS' if passed else 'FAIL'}] {name}")
if failed:
    raise SystemExit(f"{len(failed)} authentication contract check(s) failed")
print(f"Validated {len(checks)} static authentication and smoke-test contracts.")
