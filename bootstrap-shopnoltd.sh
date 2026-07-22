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
# kind's default StorageClass is 'standard' backed by local-path.
# Re-affirm it as the default (in case it's missing).
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

echo
echo "=== 3 · ingress-nginx (kind-friendly) ==="
# pinned manifest works on kind with hostPort, no extra config needed
INGRESS_VER="4.11.3"
k apply -f "https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v${INGRESS_VER}/deploy/static/provider/kind/deploy.yaml"

echo
echo "=== 4 · metrics-server (so HPA works again) ==="
k apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
# kind needs the --kubelet-insecure-tls flag
k patch -n kube-system deploy metrics-server --type=json -p='[
  {"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'

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
    defaultRequest: { cpu: 25m, memory: 64Mi,  ephemeral-storage: 128Mi }
    max:        { cpu: 2,     memory: 2Gi,   ephemeral-storage: 5Gi }
YAML
done

echo
echo "=== 7 · Node pressure (should be near 0) ==="
k describe node desktop-control-plane | grep -A 6 'Allocated resources'
k describe node desktop-worker 2>/dev/null | grep -A 6 'Allocated resources'

echo
echo "Done. Next:"
echo "  1. Apply your application manifests in this order:"
echo "     shopno-data/ → shopno-identity/ → shopno-platform/ → shopno-monitoring/"
echo "     → shopno-payments/ → shopno-apps/  (one tier at a time)"
echo "  2. Re-apply the 3 patches we know were needed:"
echo "     - billing-engine securityContext (PodSecurity restricted)"
echo "     - chatwoot image tag (v3.13.0 or v3.0, NOT :latest)"
echo "     - mail-server: drop the fix-shm-perms init container"
echo "  3. Watch pressure while you scale up:"
echo "     watch -n2 'kubectl describe node -l node-role.kubernetes.io/control-plane | grep -A6 Allocated'"
