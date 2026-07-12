#!/usr/bin/env bash
set -euo pipefail

# 1. cert-manager
echo "==> cert-manager..."
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml
kubectl -n cert-manager wait --for=condition=Available --timeout=300s deploy/cert-manager

# 2. Prometheus Operator (with CRD trimming)
echo "==> Prometheus Operator..."
"$(dirname "$0")/install-prometheus-operator.sh"

# 3. Namespaces + labels
echo "==> Namespaces..."
for ns in shopno-platform shopno-apps shopno-data shopno-identity \
          shopno-monitoring shopno-ingress shopno-payments shopno-tenants; do
  kubectl create namespace "$ns" --dry-run=client -o yaml | kubectl apply -f -
  kubectl label namespace "$ns" "name=$ns" --overwrite
done

# 4. Traefik ingress controller (lightweight alternative to nginx-ingress)
echo "==> Traefik ingress..."
kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v3.1/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml || true
helm repo add traefik https://traefik.github.io/charts
helm repo update
kubectl create namespace traefik --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install traefik traefik/traefik \
  --namespace traefik \
  --set ingressClass.enabled=true \
  --set ingressClass.isDefaultClass=true

echo "✅ Cluster bootstrap complete."
