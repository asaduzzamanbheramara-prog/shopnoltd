#!/usr/bin/env bash
# bootstrap-shopnoltd.sh — re-create namespaces + tier-0 after cluster reset
set -euo pipefail
shopt -s lastpipe

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true
k() { $DRY_RUN && echo "[DRY] kubectl $*" || kubectl "$*"; }

NSES=(
  shopno-platform shopno-data shopno-identity
  shopno-apps shopno-payments shopno-monitoring
  shopno-ingress ingress-nginx
)

echo "=== 0 · context check ==="
kubectl config current-context
kubectl get nodes -o wide

echo
echo "=== 1 · StorageClass ==="
DEFAULT_SC=$(kubectl get sc -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}' 2>/dev/null)
if [[ -z "$DEFAULT_SC" ]]; then
  echo "  no default SC, setting standard → default"
  k patch sc standard -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
else
  echo "  default SC: $DEFAULT_SC"
fi
k get sc

echo
echo "=== 2 · Namespaces ==="
for ns in "${NSES[@]}"; do
  k create namespace "$ns" --dry-run=client -o yaml | k apply -f -
done
# NetworkPolicies use this stable selector for ingress-nginx traffic.
k label namespace ingress-nginx name=ingress-nginx --overwrite

echo
echo "=== 3 · ingress-nginx (k3s/bare-metal friendly) ==="
# Pin the controller release; the controller tag is v1.11.3.
# Do not use the kind provider manifest on k3s: it requests hostPort 80/443.
INGRESS_VER="1.11.3"
k apply -f "https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v${INGRESS_VER}/deploy/static/provider/cloud/deploy.yaml"

echo
echo "=== 4 · metrics-server ==="
echo "  Metrics Server is managed by ArgoCD from k8s/metrics-server."
echo "  No bootstrap install is performed here."

echo
echo "=== 5 · cert-manager (so you can reissue certs) ==="
k apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml
echo "  waiting 30s for cert-manager webhook…"
$DRY_RUN || sleep 30
k -n cert-manager get pods

echo
echo "=== 6 · ResourceQuotas + LimitRanges per ns (single-node friendly) ==="
for ns in "${NSES[@]}"; do
  cat <<YAML | k apply -f -
apiVersion: v1
kind: LimitRange
metadata: { name: shopno-limits, namespace: $ns }
spec:
  limits:
  - type: Container
    default:    { cpu: 500m,  memory: 512Mi, ephemeral-storage: 1Gi }
    defaultRequest: { cpu: 25m, memory: 64Mi, ephemeral-storage: 128Mi }
    max:        { cpu: 2,     memory: 2Gi,   ephemeral-storage: 5Gi }
YAML
done

echo
echo "=== 7 · Node pressure ==="
kubectl get nodes -o wide

echo
echo "Done. Application manifests are reconciled by ArgoCD."
