#!/usr/bin/env bash
set -euo pipefail

echo "==> Downloading Prometheus Operator bundle..."
curl -sL https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/bundle.yaml -o /tmp/prom-bundle.yaml

# Strip the giant annotation block on each CRD so they fit etcd's 256KB cap.
python3 - <<'PY'
import re, sys
with open("/tmp/prom-bundle.yaml") as f:
    text = f.read()

# Drop the "controller-gen.kubebuilder.io/version" giant annotation block.
# Replace it with minimal annotations.
text = re.sub(
    r"controller-gen.kubebuilder.io/version: v0\.16\.3\n",
    "",
    text,
)

# Drop the entire description annotation block (the biggest offender).
text = re.sub(
    r"description: >-\n(?:[ \t]+.+\n)+",
    "",
    text,
    flags=re.MULTILINE,
)

# Apply
with open("/tmp/prom-bundle.yaml", "w") as f:
    f.write(text)
print("Bundle trimmed.")
PY

echo "==> Applying trimmed bundle..."
kubectl apply -f /tmp/prom-bundle.yaml

# Apply the deployment separately (some users only want the CRDs).
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator.yaml

echo "==> Waiting for operator..."
kubectl -n default wait --for=condition=Available --timeout=300s deploy/prometheus-operator
echo "✅ Prometheus Operator ready."
