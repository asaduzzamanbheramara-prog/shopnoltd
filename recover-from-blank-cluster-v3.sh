#!/usr/bin/env bash
# recover-from-blank-cluster-v3.sh
# Reads k8s/kustomization.yaml and applies it in 3 pressure-gated passes
# instead of one big kubectl apply -k. Re-applies the 3 known patches.
set -euo pipefail
shopt -s lastpipe

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Make sure we use the kind config in case the shell lost it
: "${KUBECONFIG:=$HOME/.kube/config}"
export KUBECONFIG

# ─── CONFIG ────────────────────────────────────────────────────────────────
# Pass A : namespaces + ingress + data + identity + monitoring
# Pass B : platform (the 22 services)
# Pass C : payments + shopno-apps (heavy hitters last)
PASS_A=(namespaces ingress/cloudflared
        services/postgres services/redis services/minio services/opensearch
        services/keycloak services/auth-service services/oauth-service
        services/prometheus services/grafana services/loki services/alertmanager)
PASS_B_SVC=$(ls -d k8s/services/*/ | xargs -n1 basename | \
             awk -F/ '{print "services/"$1}' | \
             grep -E "^services/(api-service|gateway|web-portal|admin-portal|tenant-router|domain-service|freedomain-service|mobile-api|search-service|storage-service|notification-service|report-service|analytics-service|worker-service|training-service|license-service|audit-service|event-service|foundation-service|interior-service|android-portal|ai-platform)$")
PASS_C_SVC=(services/payment-service services/exchange-service services/billing-engine
            services/chatwoot services/gitea services/code-server
            services/nextcloud services/onlyoffice services/kobotoolbox
            services/metabase services/n8n services/owncast services/superset
            services/jitsi-web services/jitsi-jicofo services/jitsi-jvb
            services/jitsi-prosody services/mail-server)
PAUSE=( 30 25 30 )

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true
k() { $DRY_RUN && echo "[DRY] kubectl $*" >&2 || kubectl "$@"; }

# ─── HELPERS ───────────────────────────────────────────────────────────────
banner() { printf '\n\033[1;33m═══ %s ═══\033[0m\n' "$*"; }
ok()     { printf '\033[0;32m[OK]\033[0m %s\n' "$*"; }
warn()   { printf '\033[0;31m[WARN]\033[0m %s\n' "$*" >&2; }
info()   { printf '\033[0;36m[INFO]\033[0m %s\n' "$*"; }

pressure() {
  for n in desktop-control-plane desktop-worker; do
    out=$(kubectl describe node "$n" 2>/dev/null \
          | awk '/Allocated resources:/{flag=1;next} flag && /^$/{flag=0} flag' \
          | head -8)
    if [[ -n "$out" ]]; then
      echo "  $n"
      echo "$out" | sed 's/^/    /'
    fi
  done
}

cpu_pct() {
  # returns current CPU request percentage, or "?" if unknown
  kubectl describe node desktop-control-plane 2>/dev/null \
    | awk '/^  cpu[[:space:]]/{print $2; exit}' || echo "?"
}

apply_subpath() {
  local rel="$1"  # e.g. "services/postgres"
  local path="k8s/$rel"
  if [[ ! -d "$path" ]]; then
    warn "  $path does not exist — skipped"; return
  fi
  info "  kustomize: $path"
  $DRY_RUN && { echo "    [DRY] kubectl apply -k $path"; return; }
  # kustomize apply; never fail the whole run on a single bad service
  if ! kubectl apply -k "$path" 2>&1 | sed 's/^/    /'; then
    warn "  $path failed — continuing"
  fi
}

gate() {
  local label="$1"; local max="$2"
  local p
  p=$(cpu_pct)
  info "  gate [$label]: CPU reqs at ${p}%, threshold ${max}%"
  if [[ "$p" =~ ^[0-9]+%$ ]]; then
    local n=${p%\%}
    if (( n > max )); then
      warn "  above threshold! Pausing 60s for things to settle…"
      sleep 60
    fi
  fi
}

# ─── PHASE 0: DIAGNOSTICS ──────────────────────────────────────────────────
banner "PHASE 0 · Diagnostics"
info "KUBECONFIG=$KUBECONFIG"
info "context:    $(kubectl config current-context 2>&1 || echo NONE)"

if ! kubectl get nodes >/dev/null 2>&1; then
  warn "  API server unreachable. Trying to recover the kind cluster…"
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q '^desktop-control-plane$'; then
    info "  starting existing kind containers…"
    docker start desktop-control-plane desktop-worker || true
    sleep 25
  else
    info "  no kind containers — recreating from ~/.kube/kind-config.yaml…"
    kind create cluster --name desktop --config ~/.kube/kind-config.yaml \
      --kubeconfig "$KUBECONFIG"
  fi
  kubectl get nodes
fi

kubectl get nodes -o custom-columns=NAME:.metadata.name,ROLES:.metadata.labels,\
CPU:.status.allocatable.cpu,MEM:.status.allocatable.memory
info "storage classes:"; kubectl get sc
info "starting pressure:"; pressure

# ─── PHASE 1: NAMESPACES (always first) ─────────────────────────────────────
banner "PHASE 1 · Namespaces"
k apply -f k8s/namespaces/
ok "k8s/namespaces/ applied"

# ─── PHASE 2: PASS A (ingress + data + identity + monitoring) ──────────────
banner "PHASE 2 · Pass A (foundation)"
for s in "${PASS_A[@]}"; do apply_subpath "$s"; done
gate "post-PassA" 70
$DRY_RUN || sleep "${PAUSE[0]}"
pressure

# ─── PHASE 3: PASS B (platform services, 22 of them) ──────────────────────
banner "PHASE 3 · Pass B (platform)"
for s in $PASS_B_SVC; do apply_subpath "$s"; done
gate "post-PassB" 70
$DRY_RUN || sleep "${PAUSE[1]}"
pressure

# ─── PHASE 4: PASS C (payments + shopno-apps) ─────────────────────────────
banner "PHASE 4 · Pass C (payments + apps)"
read -rp "Apply Pass C (payment + shopno-apps) now? [y/N] " ans
if [[ "${ans,,}" == "y" ]]; then
  for s in "${PASS_C_SVC[@]}"; do apply_subpath "$s"; done
  gate "post-PassC" 75
  $DRY_RUN || sleep "${PAUSE[2]}"
else
  warn "skipped Pass C — run with --include-apps later or scale manually"
fi
pressure

# ─── PHASE 5: KNOWN PATCHES ────────────────────────────────────────────────
banner "PHASE 5 · Known patches"

# 5a) billing-engine securityContext
if kubectl get deploy billing-engine -n shopno-payments >/dev/null 2>&1; then
  info "  billing-engine → restricted PodSecurity"
  kubectl -n shopno-payments patch deploy billing-engine --type=json -p='[
    {"op":"add","path":"/spec/template/spec/securityContext",
     "value":{"runAsNonRoot":true,"seccompProfile":{"type":"RuntimeDefault"}}},
    {"op":"add","path":"/spec/template/spec/containers/0/securityContext",
     "value":{"allowPrivilegeEscalation":false,
              "capabilities":{"drop":["ALL"]},
              "runAsNonRoot":true,
              "seccompProfile":{"type":"RuntimeDefault"}}}]' 2>&1 | tail -1 \
    || warn "  (already applied)"
else
  warn "  billing-engine not present"
fi

# 5b) chatwoot — pin tag
if kubectl get deploy chatwoot -n shopno-apps >/dev/null 2>&1; then
  info "  chatwoot → pin image"
  for img in "chatwoot/chatwoot-web:v3.13.0" "chatwoot/chatwoot-web:v3.0"; do
    if kubectl -n shopno-apps set image deploy/chatwoot "chatwoot=$img" 2>/dev/null \
         | grep -q "image updated"; then
      ok "  chatwoot → $img"; break
    fi
  done
else
  warn "  chatwoot not present"
fi

# 5c) mail-server — drop redundant init
if kubectl get deploy mail-server -n default >/dev/null 2>&1; then
  info "  mail-server → drop init container"
  kubectl -n default patch deploy mail-server --type=json \
    -p='[{"op":"remove","path":"/spec/template/spec/initContainers"}]' \
    2>/dev/null || warn "  (init already gone)"
  kubectl -n default delete pods -l app=mail-server --grace-period=0 --force 2>/dev/null || true
else
  warn "  mail-server not present"
fi

# 5d) Pending PVCs → local-path
info "  re-binding Pending PVCs to local-path"
kubectl get pvc -A --no-headers 2>/dev/null \
  | awk '$3=="Pending" {print $1" "$2}' \
  | while read -r ns pvc; do
      [[ -z "$ns" ]] && continue
      info "    $ns/$pvc"
      kubectl -n "$ns" patch pvc "$pvc" --type=json \
        -p='[{"op":"replace","path":"/spec/storageClassName","value":"local-path"}]' \
        2>/dev/null || warn "    (manual recreate needed)"
    done

# ─── PHASE 6: VERIFY ────────────────────────────────────────────────────────
banner "PHASE 6 · Verify"
if ! $DRY_RUN; then
  for i in 1 2 3 4 5 6 7 8 9 10; do
    bad=$(kubectl get pods -A --no-headers 2>/dev/null \
          | awk '$3!="Running" && $3!="Completed"' | wc -l)
    running=$(kubectl get pods -A --no-headers 2>/dev/null \
              | awk '$3=="Running"' | wc -l)
    total=$(kubectl get pods -A --no-headers 2>/dev/null | wc -l)
    echo "  [t+${i}*30s] pods=$total running=$running not-ok=$bad"
    if (( bad == 0 )); then ok "All pods Running/Completed"; break; fi
    sleep 30
  done
fi

banner "Done"
pressure
