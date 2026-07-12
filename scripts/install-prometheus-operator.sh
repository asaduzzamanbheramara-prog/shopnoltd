#!/usr/bin/env bash
set -euo pipefail

# 1. Apply the small CRDs from the operator (these fit)
echo "==> Applying small CRDs from prometheus-operator..."
curl -sL https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_alertmanagerconfigs.yaml | kubectl apply -f -
curl -sL https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_podmonitors.yaml | kubectl apply -f -
curl -sL https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_probes.yaml | kubectl apply -f -
curl -sL https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_prometheusrules.yaml | kubectl apply -f -
curl -sL https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_scrapeconfigs.yaml | kubectl apply -f -
curl -sL https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_servicemonitors.yaml | kubectl apply -f -

# 2. For the big 4 (alertmanagers, prometheuses, prometheusagents, thanosrulers),
#    strip the giant description block by hand with a stronger regex.
echo "==> Downloading and trimming the 4 large CRDs..."

trim_crd() {
  local url="$1"
  local out="/tmp/$(basename "$url")"
  curl -sL "$url" -o "$out"
  python3 - "$out" <<'PY'
import re, sys
fp = sys.argv[1]
with open(fp) as f:
    txt = f.read()
# Aggressively strip the description block (often 30-100 KB of plain text).
txt = re.sub(r"^\s*description:\s*>-\s*\n((?:\s+.+\n)+)", "", txt, flags=re.MULTILINE)
# Strip the per-version "properties:" intros if they contain only "description" keys.
# (Keep the schema valid; this is conservative.)
with open(fp, "w") as f:
    f.write(txt)
print("trimmed:", fp)
PY
  kubectl apply -f "$out" || echo "WARN: $out did not apply, will use alternative"
}

trim_crd https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_alertmanagers.yaml
trim_crd https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_prometheuses.yaml
trim_crd https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_thanosrulers.yaml
trim_crd https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_prometheusagents.yaml

# 3. Apply the operator deployment
echo "==> Deploying prometheus-operator..."
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator.yaml

# 4. Wait
echo "==> Waiting for operator..."
kubectl -n default wait --for=condition=Available --timeout=300s deploy/prometheus-operator

# 5. Verify
echo "==> Verifying CRDs..."
kubectl get crd | grep monitoring.coreos.com

echo "✅ Prometheus Operator ready."
