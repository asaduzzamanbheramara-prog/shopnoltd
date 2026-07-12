#!/usr/bin/env bash
set -euo pipefail
# Installs the operator CRDs that Shopnoltd depends on.

echo "==> Installing cert-manager (for TLS)..."
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml
kubectl -n cert-manager wait --for=condition=Available --timeout=180s deploy/cert-manager

echo "==> Installing Prometheus Operator (for ServiceMonitor)..."
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/bundle.yaml
kubectl -n default wait --for=condition=Available --timeout=180s deploy/prometheus-operator

echo "==> Creating Shopnoltd namespaces..."
for ns in shopno-platform shopno-apps shopno-data shopno-identity \
          shopno-monitoring shopno-ingress shopno-payments shopno-tenants; do
  kubectl create namespace "$ns" --dry-run=client -o yaml | kubectl apply -f -
done

echo "==> Labelling namespaces for NetworkPolicy selectors..."
kubectl label namespace shopno-ingress      name=shopno-ingress      --overwrite
kubectl label namespace shopno-platform     name=shopno-platform     --overwrite
kubectl label namespace shopno-data         name=shopno-data         --overwrite
kubectl label namespace shopno-identity     name=shopno-identity     --overwrite
kubectl label namespace shopno-monitoring   name=shopno-monitoring   --overwrite
kubectl label namespace shopno-apps         name=shopno-apps         --overwrite
kubectl label namespace shopno-payments     name=shopno-payments     --overwrite

echo "✅ Cluster bootstrap complete."
