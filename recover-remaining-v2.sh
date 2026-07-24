#!/usr/bin/env bash
# recover-remaining-v2.sh — finishes cluster recovery
set -uo pipefail
shopt -s lastpipe
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
ROOT="/mnt/c/Users/asadu/PROJECTS/shopnoltd"
cd "$ROOT"

banner() { printf '\n\033[1;33m═══ %s ═══\033[0m\n' "$*"; }
ok()     { printf '\033[0;32m[OK]\033[0m %s\n' "$*"; }
warn()   { printf '\033[0;31m[WARN]\033[0m %s\n' "$*" >&2; }
info()   { printf '\033[0;36m[INFO]\033[0m %s\n' "$*"; }

# Phase 1: re-apply namespaces
banner "PHASE 1 · Namespaces"
kubectl apply -f k8s/namespaces/

# Phase 2: per-namespace kustomize (using ABSOLUTE paths this time)
banner "PHASE 2 · Per-namespace kustomize"
declare -A NS_SVCS
while read -r ns svc; do
  NS_SVCS[$ns]+="$svc "
done < <(
  for d in k8s/services/*/; do
    svc=$(basename "$d")
    ns=$(awk '/^namespace:[[:space:]]*/{print $2; exit}' "$d/kustomization.yaml" 2>/dev/null)
    [[ -z "$ns" ]] && continue
    echo "$ns $svc"
  done
)

for ns in "${!NS_SVCS[@]}"; do
  tmpdir=$(mktemp -d)
  cat > "$tmpdir/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
EOF
  for svc in ${NS_SVCS[$ns]}; do
    # ABSOLUTE PATH — fixes the /tmp/services bug
    echo "  - $ROOT/k8s/services/$svc" >> "$tmpdir/kustomization.yaml"
  done
  info "  $ns: ${NS_SVCS[$ns]}"
  if kubectl apply -k "$tmpdir" 2>&1 | grep -E "(error|Error|namespace.*not found)" | head -3; then
    warn "  $ns: some errors (will re-apply individually)"
  else
    ok "  $ns: applied"
  fi
  rm -rf "$tmpdir"
done

# Phase 3: individual re-apply for any service that still has issues
banner "PHASE 3 · Individual re-apply"
for d in k8s/services/*/; do
  svc=$(basename "$d")
  kubectl apply -k "$d" >/dev/null 2>&1 && info "  $svc: applied" || true
done

# Phase 4: restart CrashLoopBackOff pods
banner "PHASE 4 · Restart CrashLoopBackOff pods"
kubectl get pods -A --no-headers 2>/dev/null \
  | awk '$4=="CrashLoopBackOff" {print $1, $2}' \
  | while read -r ns pod; do
      info "  deleting $ns/$pod"
      kubectl delete pod "$pod" -n "$ns" --grace-period=0 --force 2>/dev/null || true
    done

# Phase 5: wait + verify
banner "PHASE 5 · Verify"
for i in 1 2 3 4 5 6 7 8 9 10; do
  bad=$(kubectl get pods -A --no-headers 2>/dev/null | awk '$3!="Running" && $3!="Completed"' | wc -l)
  running=$(kubectl get pods -A --no-headers 2>/dev/null | awk '$3=="Running"' | wc -l)
  total=$(kubectl get pods -A --no-headers 2>/dev/null | wc -l)
  echo "  [t+${i}*30s] total=$total running=$running not-ok=$bad"
  [[ $bad -eq 0 ]] && { ok "all pods healthy"; break; }
  sleep 30
done

banner "DONE — breakdown of remaining"
kubectl get pods -A --no-headers 2>/dev/null | grep -vE " Running | Completed " \
  | awk '{print $4}' | sort | uniq -c | sort -rn
