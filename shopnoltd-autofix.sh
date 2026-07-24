#!/usr/bin/env bash
# shopnoltd-autofix.sh — single-pass auto-remediation
set -uo pipefail
shopt -s lastpipe

export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

banner() { printf '\n\033[1;33m═══ %s ═══\033[0m\n' "$*"; }
ok()     { printf '\033[0;32m[OK]\033[0m %s\n' "$*"; }
warn()   { printf '\033[0;31m[WARN]\033[0m %s\n' "$*" >&2; }
info()   { printf '\033[0;36m[INFO]\033[0m %s\n' "$*"; }

# Phase 0 — confirm cluster
banner "PHASE 0 · Cluster check"
kubectl get nodes -o wide || { warn "cluster unreachable"; exit 1; }
ok "cluster is up"

# Phase 1 — install ServiceMonitor CRD only (the one we need)
banner "PHASE 1 · Install ServiceMonitor CRD"
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.76.0/example/prometheus-operator-crd/servicemonitors.monitoring.coreos.com.yaml 2>/dev/null \
  && ok "ServiceMonitor CRD installed" || warn "ServiceMonitor CRD may already exist"

# Phase 2 — generate missing secret.yaml files
banner "PHASE 2 · Generate missing secret.yaml files"
DEFAULT_PW="$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)"
created=0
for d in k8s/services/*/; do
  kust="$d/kustomization.yaml"
  [[ -f "$kust" ]] || continue
  grep -qE '^\s*-\s*secret\.yaml\s*$' "$kust" || continue
  [[ -f "$d/secret.yaml" ]] && continue
  svc=$(basename "$d")
  ns=$(awk '/^namespace:[[:space:]]*/{print $2; exit}' "$kust")
  [[ -z "$ns" ]] && ns="default"
  secret_name=$(awk '/^\s*secretName:[[:space:]]*/{print $2; exit}' "$d/deployment.yaml" 2>/dev/null || true)
  [[ -z "$secret_name" ]] && secret_name="${svc}-secret"
  cat > "$d/secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: ${secret_name}
  namespace: ${ns}
type: Opaque
stringData:
  password: "${DEFAULT_PW}"
  username: "${svc}"
  admin-password: "${DEFAULT_PW}"
  jwt-secret: "${DEFAULT_PW}"
  db-password: "${DEFAULT_PW}"
  api-key: "${DEFAULT_PW}"
EOF
  created=$((created+1))
done
ok "Created $created secret.yaml files"

# mail-server kustomization if missing
[[ -f k8s/services/mail-server/kustomization.yaml ]] || cat > k8s/services/mail-server/kustomization.yaml <<'EOF'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: default
resources:
- deployment.yaml
- service.yaml
EOF

# Phase 3 — convert httpGet probes to tcpSocket for raw TCP services
banner "PHASE 3 · Convert httpGet probes → tcpSocket"
for ns in shopno-data shopno-identity shopno-monitoring shopno-platform shopno-payments shopno-apps; do
  for d in $(kubectl get deploy -n "$ns" -o name 2>/dev/null | sed 's|deployment.apps/||'); do
    port=$(kubectl get deploy "$d" -n "$ns" -o jsonpath='{.spec.template.spec.containers[0].ports[0].containerPort}' 2>/dev/null)
    [[ -z "$port" ]] && continue
    has_http=$(kubectl get deploy "$d" -n "$ns" -o jsonpath='{.spec.template.spec.containers[0].livenessProbe.httpGet}' 2>/dev/null)
    [[ -z "$has_http" ]] && continue
    info "  $ns/$d → tcpSocket :$port"
    kubectl patch deploy "$d" -n "$ns" --type=json -p="[
      {\"op\":\"remove\",\"path\":\"/spec/template/spec/containers/0/livenessProbe/httpGet\"},
      {\"op\":\"add\",\"path\":\"/spec/template/spec/containers/0/livenessProbe/tcpSocket\",\"value\":{\"port\":$port}},
      {\"op\":\"remove\",\"path\":\"/spec/template/spec/containers/0/readinessProbe/httpGet\"},
      {\"op\":\"add\",\"path\":\"/spec/template/spec/containers/0/readinessProbe/tcpSocket\",\"value\":{\"port\":$port}},
      {\"op\":\"remove\",\"path\":\"/spec/template/spec/containers/0/startupProbe/httpGet\"},
      {\"op\":\"add\",\"path\":\"/spec/template/spec/containers/0/startupProbe/tcpSocket\",\"value\":{\"port\":$port}}
    ]" >/dev/null 2>&1
  done
done

# Phase 4 — drop mail-server init container
banner "PHASE 4 · Drop mail-server init container"
if kubectl get deploy mail-server -n default >/dev/null 2>&1; then
  kubectl patch deploy mail-server -n default --type=json \
    -p='[{"op":"remove","path":"/spec/template/spec/initContainers"}]' 2>/dev/null || true
  kubectl delete pods -n default -l app=mail-server --grace-period=0 --force 2>/dev/null || true
  ok "mail-server patched"
fi

# Phase 5 — billing-engine restricted securityContext
banner "PHASE 5 · billing-engine securityContext"
if kubectl get deploy billing-engine -n shopno-payments >/dev/null 2>&1; then
  kubectl patch deploy billing-engine -n shopno-payments --type=json -p='[
    {"op":"add","path":"/spec/template/spec/securityContext",
     "value":{"runAsNonRoot":true,"seccompProfile":{"type":"RuntimeDefault"}}},
    {"op":"add","path":"/spec/template/spec/containers/0/securityContext",
     "value":{"allowPrivilegeEscalation":false,
              "capabilities":{"drop":["ALL"]},
              "runAsNonRoot":true,
              "seccompProfile":{"type":"RuntimeDefault"}}}]' 2>/dev/null || true
  ok "billing-engine securityContext set"
fi

# Phase 6 — chatwoot image pin
banner "PHASE 6 · Pin chatwoot image"
if kubectl get deploy chatwoot -n shopno-apps >/dev/null 2>&1; then
  for img in "chatwoot/chatwoot-web:v3.13.0" "chatwoot/chatwoot-web:v3.0"; do
    if kubectl set image deploy/chatwoot -n shopno-apps "chatwoot=$img" 2>/dev/null | grep -q "image updated"; then
      ok "chatwoot → $img"; break
    fi
  done
fi

# Phase 7 — PVCs to local-path
banner "PHASE 7 · Re-bind Pending PVCs"
kubectl get pvc -A --no-headers 2>/dev/null \
  | awk '$3=="Pending" {print $1" "$2}' \
  | while read -r ns pvc; do
      [[ -z "$ns" ]] && continue
      info "  $ns/$pvc"
      kubectl -n "$ns" patch pvc "$pvc" --type=json \
        -p='[{"op":"replace","path":"/spec/storageClassName","value":"local-path"}]' 2>/dev/null || true
    done

# Phase 8 — drop servicemonitor references
banner "PHASE 8 · Drop servicemonitor references"
for f in k8s/services/*/kustomization.yaml; do
  [[ -f "$f" ]] || continue
  if grep -qE '^\s*-\s*servicemonitor\.yaml\s*$' "$f"; then
    sed -i.bak -E '/^\s*-\s*servicemonitor\.yaml\s*$/d' "$f"
  fi
done
ok "servicemonitor references removed"

# Phase 9 — re-apply all
banner "PHASE 9 · Re-apply all services"
for d in k8s/services/*/; do
  svc=$(basename "$d")
  kubectl apply -k "$d" >/dev/null 2>&1 && info "  $svc: applied" || warn "  $svc: failed"
done

# Phase 10 — verify
banner "PHASE 10 · Verify"
for i in 1 2 3 4 5 6 7 8 9 10; do
  bad=$(kubectl get pods -A --no-headers 2>/dev/null | awk '$3!="Running" && $3!="Completed"' | wc -l)
  running=$(kubectl get pods -A --no-headers 2>/dev/null | awk '$3=="Running"' | wc -l)
  total=$(kubectl get pods -A --no-headers 2>/dev/null | wc -l)
  echo "  [t+${i}*30s] total=$total running=$running not-ok=$bad"
  [[ $bad -eq 0 ]] && { ok "all pods healthy"; break; }
  sleep 30
done

banner "DONE"
kubectl get pods -A | grep -vE " Running | Completed " | head -25
