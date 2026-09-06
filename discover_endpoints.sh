#!/usr/bin/env bash
# READ-ONLY. Lists every Ingress -> hostname -> backend Service mapping.
# Run this first so we know the real public URLs before testing anything.
set -euo pipefail
export KUBECONFIG=/home/shopno/k3s.yaml

echo "============================================================"
echo "INGRESS HOSTNAME MAP"
echo "============================================================"

kubectl get ingress -A -o json | python3 -c '
import json, sys
data = json.load(sys.stdin)
rows = []
for item in data["items"]:
    ns = item["metadata"]["namespace"]
    name = item["metadata"]["name"]
    rules = item.get("spec", {}).get("rules", [])
    for r in rules:
        host = r.get("host", "?")
        paths = r.get("http", {}).get("paths", [])
        for p in paths:
            svc = p.get("backend", {}).get("service", {}).get("name", "?")
            port = p.get("backend", {}).get("service", {}).get("port", {})
            portstr = port.get("number", port.get("name", "?"))
            path = p.get("path", "/")
            rows.append((ns, host, path, svc, str(portstr)))
rows.sort()
print(f"{"NAMESPACE":20s} {"HOST":45s} {"PATH":10s} {"SERVICE":30s} PORT")
for ns, host, path, svc, port in rows:
    print(f"{ns:20s} {host:45s} {path:10s} {svc:30s} {port}")
'

echo
echo "============================================================"
echo "KEYCLOAK CLIENT CONFIG (to confirm direct-grant / auth flow)"
echo "============================================================"
echo "shopnoltd-web client public settings (redirect URIs, direct access grants):"
kubectl get configmap keycloak-realm -n shopno-identity -o jsonpath='{.data.realm-shopnoltd\.json}' 2>/dev/null \
  | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception as e:
    print("Could not parse realm JSON:", e)
    sys.exit(0)
for c in data.get("clients", []):
    if "shopnoltd" in c.get("clientId", "").lower() or "web" in c.get("clientId", "").lower():
        print(f"clientId: {c.get(\"clientId\")}")
        print(f"  directAccessGrantsEnabled: {c.get(\"directAccessGrantsEnabled\")}")
        print(f"  publicClient: {c.get(\"publicClient\")}")
        print(f"  redirectUris: {c.get(\"redirectUris\")}")
        print(f"  webOrigins: {c.get(\"webOrigins\")}")
        print()
' || echo "(realm not stored in this ConfigMap as JSON, or key name differs — check manually if this prints nothing)"

echo
echo "============================================================"
echo "SERVICES WITH 'blog' IN NAME (any namespace)"
echo "============================================================"
kubectl get svc -A | grep -i blog || echo "(no service with 'blog' in its name — confirm the CMS service's actual k8s name)"
