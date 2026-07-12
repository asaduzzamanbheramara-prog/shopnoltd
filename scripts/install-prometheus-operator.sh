#!/usr/bin/env bash
set -euo pipefail

# Install the 6 small CRDs (your manifests only use ServiceMonitor anyway)
echo "==> Installing small Prometheus CRDs..."
for crd in alertmanagerconfigs podmonitors probes prometheusrules scrapeconfigs servicemonitors; do
  curl -fsSL "https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_${crd}.yaml" \
    -o "/tmp/${crd}.yaml"
  kubectl apply -f "/tmp/${crd}.yaml"
done

# Deploy the operator
echo "==> Deploying prometheus-operator..."
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/rbac/prometheus-operator/prometheus-operator-deployment.yaml

# Wait
kubectl -n default wait --for=condition=Available --timeout=300s deploy/prometheus-operator

# Verify
kubectl get crd | grep monitoring.coreos.com
echo "✅ Prometheus Operator ready (small CRDs only)."
