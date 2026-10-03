import json
import os
import ssl
import time
import urllib.error
import urllib.request

API = "https://kubernetes.default.svc:443"
TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

with open(TOKEN_PATH, encoding="utf-8") as handle:
    token = handle.read().strip()

context = ssl.create_default_context(cafile=CA_PATH)
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
}


def request(path, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode()
    request_obj = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers=headers
        | (
            {"Content-Type": "application/merge-patch+json"}
            if body is not None
            else {}
        ),
    )
    last_error = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request_obj, context=context, timeout=15) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 4:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Kubernetes API request failed: {last_error}")


source_path = "/api/v1/namespaces/shopno-identity/secrets/keycloak-secret"
target_path = "/api/v1/namespaces/shopno-platform/secrets/freedomain-service-secret"

source = request(source_path)
source_data = source.get("data", {})
password = source_data.get("KC_BOOTSTRAP_ADMIN_PASSWORD")
if not password:
    raise RuntimeError("keycloak-secret is missing KC_BOOTSTRAP_ADMIN_PASSWORD")

try:
    request(target_path)
except urllib.error.HTTPError as exc:
    if exc.code == 404:
        raise RuntimeError(
            "freedomain-service-secret does not exist; refusing to create a partial secret"
        ) from exc
    raise

request(
    target_path,
    method="PATCH",
    body={"data": {"KC_BOOTSTRAP_ADMIN_PASSWORD": password}},
)

print("Synchronized KC_BOOTSTRAP_ADMIN_PASSWORD into the platform-local secret.")
