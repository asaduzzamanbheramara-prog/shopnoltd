#!/usr/bin/env bash
set -euo pipefail
# Install Prometheus Operator using the stripped bundle (no huge annotations).
echo "==> Installing Prometheus Operator (stripped bundle)..."
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/stripped-down-crds.yaml
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/bundle.yaml

# Some CRDs hit the 256KB annotation cap on etcd, so we use the stripped-down
# version of those that fit. Fall back to manual serviceMonitor CRD if needed.
kubectl apply -f - <<'EOF'
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: servicemonitors.monitoring.coreos.com
spec:
  group: monitoring.coreos.com
  scope: Namespaced
  names:
    kind: ServiceMonitor
    listKind: ServiceMonitorList
    singular: servicemonitor
    plural: servicemonitors
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          x-kubernetes-preserve-unknown-fields: true
EOF

kubectl -n default wait --for=condition=Available --timeout=180s deploy/prometheus-operator
echo "✅ Prometheus Operator ready."
