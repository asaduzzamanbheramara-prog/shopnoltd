#!/usr/bin/env bash
# shopnoltd-recover-v2.sh — fixed bash syntax, aggressive single-node scale-down
set -uo pipefail
shopt -s lastpipe

LOG_DIR="${LOG_DIR:-/tmp/shopnoltd-recovery}"
DRY_RUN=false
SELECTED_PHASES="0,1,2,3,4,5,6"

# Tier-0 : critical (will be at 1 replica)
TIER0=(
  "ingress-nginx/ingress-nginx-controller"
  "shopno-data/postgres" "shopno-data/redis"
  "shopno-identity/keycloak" "shopno-identity/auth-service" "shopno-identity/oauth-service"
  "shopno-platform/gateway" "shopno-platform/web-portal" "shopno-platform/tenant-router"
  "shopno-platform/api-service"
  "shopno-monitoring/prometheus" "shopno-monitoring/grafana"
)
# Tier-2 : platform — on, smaller footprint
TIER2=(
  "shopno-data/minio" "shopno-data/opensearch"
  "shopno-platform/domain-service" "shopno-platform/license-service"
  "shopno-platform/notification-service" "shopno-platform/scheduler-service"
  "shopno-monitoring/loki" "shopno-monitoring/alertmanager"
  "shopno-payments/payment-service" "shopno-payments/exchange-service" "shopno-payments/billing-engine"
)
# Tier-3 : apps — OFF, you turn on what you need
TIER3=(
  "shopno-apps/jitsi-web" "shopno-apps/jitsi-jicofo" "shopno-apps/jitsi-jvb" "shopno-apps/jitsi-prosody"
  "shopno-apps/chatwoot" "shopno-apps/code-server" "shopno-apps/owncast"
  "shopno-apps/nextcloud" "shopno-apps/onlyoffice"
  "shopno-apps/n8n" "shopno-apps/metabase" "shopno-apps/superset"
  "shopno-apps/kobotoolbox" "shopno-apps/gitea"
)

CPU_REQ=25m;  CPU_LIM=500m
MEM_REQ=64Mi; MEM_LIM=512Mi
EPH_REQ=128Mi;EPH_LIM=1Gi

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/recover-$(date +%Y%m%d-%H%M%S).log"

ts()  { date '+%H:%M:%S'; }
log() { printf '%s %s %s\n' "$(ts)" "$1" "$2" | tee -a "$LOG_FILE"; }
info(){ log "[INFO]" "$1"; }
warn(){ log "[WARN]" "$1" >&2; }
ok()  { log "[OK]  " "$1"; }
hdr() { printf '\n=== %s ===\n' "$*" | tee -a "$LOG_FILE"; }

kctl() {
  if $DRY_RUN; then echo "  [DRY] kubectl $*" | tee -a "$LOG_FILE"
  else kubectl "$@"; fi
}
phase_active() { [[ ",$SELECTED_PHASES," == *",$1,"* ]]; }

# ─── PHASE 0 ────────────────────────────────────────────────────────────────
p0_diagnose() {
  hdr "PHASE 0 · Diagnostics"
  info "Node pressure (Allocated resources):"
  kctl describe node desktop-control-plane 2>/dev/null \
    | grep -A 6 "Allocated resources:" | head -8
  info "Status counts:"
  for s in Running Pending CrashLoopBackOff ImagePullBackOff Terminating Error; do
    # AWK-based counting — no parens in regex, no bash subshell surprises
    n=$(kubectl get pods -A --no-headers 2>/dev/null \
         | awk -v s="$s" '$3==s' | wc -l)
    [[ $n -gt 0 ]] && warn "  $s: $n"
  done
  # Init:0/1 etc.
  n=$(kubectl get pods -A --no-headers 2>/dev/null \
       | awk '$3 ~ /^Init:/' | wc -l)
  [[ $n -gt 0 ]] && warn "  Init: $n"
  info "Storage classes:"
  kctl get sc
}

# ─── PHASE 1 ────────────────────────────────────────────────────────────────
p1_evict() {
  hdr "PHASE 1 · Force-evict stuck pods"
  local total=0
  # Terminating
  while read -r line; do
    [[ -z "$line" ]] && continue
    local ns="${line%% *}"; local pod="${line##* }"
    info "  evict $ns/$pod"
    kctl delete pod "$pod" -n "$ns" --grace-period=0 --force 2>/dev/null \
      || warn "  gone: $pod"
    total=$((total+1))
  done < <(kubectl get pods -A --field-selector=status.phase=Terminating \
            --no-headers 2>/dev/null | awk '{print $1" "$2}')
  # Pending > 0/1 with no node
  while read -r line; do
    [[ -z "$line" ]] && continue
    local ns="${line%% *}"; local pod="${line##* }"
    info "  evict pending $ns/$pod"
    kctl delete pod "$pod" -n "$ns" --grace-period=0 --force 2>/dev/null \
      || warn "  gone: $pod"
    total=$((total+1))
  done < <(kubectl get pods -A --no-headers 2>/dev/null \
            | awk '$3=="0/1" && $4=="Pending" {print $1" "$2}')
  ok "Evicted $total stuck pods"

  # Orphaned ReplicaSets (desired=0 but still present)
  info "Cleaning orphaned ReplicaSets..."
  kubectl get rs -A --no-headers 2>/dev/null \
    | awk '$3==0 && $4>0 {print $1" "$2}' \
    | while read -r ns rs; do
        [[ -z "$ns" ]] && continue
        info "  delete RS $ns/$rs"
        kctl delete rs "$rs" -n "$ns" 2>/dev/null
      done
}

# ─── PHASE 2 ────────────────────────────────────────────────────────────────
p2_fix_config() {
  hdr "PHASE 2 · Targeted config fixes"

  # 2a) billing-engine — PodSecurity restricted
  if kctl get deploy billing-engine -n shopno-payments >/dev/null 2>&1; then
    info "Patching billing-engine securityContext..."
    kctl patch deploy billing-engine -n shopno-payments --type=json -p='[
      {"op":"add","path":"/spec/template/spec/securityContext",
       "value":{"runAsNonRoot":true,"seccompProfile":{"type":"RuntimeDefault"}}},
      {"op":"add","path":"/spec/template/spec/containers/0/securityContext",
       "value":{"allowPrivilegeEscalation":false,
                "capabilities":{"drop":["ALL"]},
                "runAsNonRoot":true,
                "seccompProfile":{"type":"RuntimeDefault"}}}]' 2>&1 | tail -1 \
       || warn "billing-engine patch may already be applied"
  else
    warn "billing-engine deployment not found"
  fi

  # 2b) chatwoot — pin tag
  if kctl get deploy chatwoot -n shopno-apps >/dev/null 2>&1; then
    info "Pinning chatwoot image..."
    for img in "chatwoot/chatwoot-web:v3.13.0" "chatwoot/chatwoot-web:v3.0"; do
      if kctl set image deploy/chatwoot -n shopno-apps "chatwoot=$img" 2>/dev/null \
           | grep -q "image updated"; then
        ok "  chatwoot → $img"; break
      fi
    done
  fi

  # 2c) mail-server — drop redundant init
  if kctl get deploy mail-server -n default >/dev/null 2>&1; then
    info "Removing mail-server init container..."
    kctl patch deploy mail-server -n default --type=json \
      -p='[{"op":"remove","path":"/spec/template/spec/initContainers"}]' 2>/dev/null \
      || warn "  init already removed"
    kctl delete pods -n default -l app=mail-server --grace-period=0 --force \
      2>/dev/null || true
  fi

  # 2d) Pending PVCs → local-path
  info "Re-binding Pending PVCs to local-path..."
  kubectl get pvc -A --no-headers 2>/dev/null \
    | awk '$3=="Pending" {print $1" "$2}' \
    | while read -r ns pvc; do
        [[ -z "$ns" ]] && continue
        info "  $ns/$pvc"
        kctl patch pvc "$pvc" -n "$ns" --type=json \
          -p='[{"op":"replace","path":"/spec/storageClassName","value":"local-path"}]' \
          2>/dev/null || warn "    manual recreate needed"
      done
}

# ─── PHASE 3 ────────────────────────────────────────────────────────────────
p3_resize() {
  hdr "PHASE 3 · Right-size requests ($CPU_REQ/$CPU_LIM CPU, $MEM_REQ/$MEM_LIM mem)"
  local patched=0
  local all=("${TIER0[@]}" "${TIER2[@]}" "${TIER3[@]}")
  for d in "${all[@]}"; do
    local ns="${d%/*}"; local name="${d#*/}"
    kctl get deploy "$name" -n "$ns" >/dev/null 2>&1 || continue
    if kctl patch deploy "$name" -n "$ns" --type=json -p="[
      {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/resources\",
       \"value\":{
         \"requests\":{\"cpu\":\"$CPU_REQ\",\"memory\":\"$MEM_REQ\",\"ephemeral-storage\":\"$EPH_REQ\"},
         \"limits\":  {\"cpu\":\"$CPU_LIM\",\"memory\":\"$MEM_LIM\",\"ephemeral-storage\":\"$EPH_LIM\"}
       }}]" >/dev/null 2>&1; then
      patched=$((patched+1))
    fi
  done
  ok "Right-sized $patched deployments"
}

# ─── PHASE 4 ────────────────────────────────────────────────────────────────
p4_prioritise() {
  hdr "PHASE 4 · Prioritise (Tier-3 → 0, Tier-0/2 → 1)"
  for d in "${TIER3[@]}"; do
    local ns="${d%/*}"; local name="${d#*/}"
    kctl get deploy "$name" -n "$ns" >/dev/null 2>&1 || continue
    kctl scale deploy "$name" -n "$ns" --replicas=0 2>/dev/null || true
  done
  for d in "${TIER0[@]}" "${TIER2[@]}"; do
    local ns="${d%/*}"; local name="${d#*/}"
    kctl get deploy "$name" -n "$ns" >/dev/null 2>&1 || continue
    kctl scale deploy "$name" -n "$ns" --replicas=1 2>/dev/null || true
  done
  ok "Prioritisation applied"
}

# ─── PHASE 5 ────────────────────────────────────────────────────────────────
p5_restart() {
  hdr "PHASE 5 · Rolling restart in order (L1 → L2 → L3 → L4 → L5)"
  local order=(
    "shopno-data/postgres" "shopno-data/redis" "shopno-data/minio" "shopno-data/opensearch"
    "shopno-identity/keycloak" "shopno-identity/auth-service" "shopno-identity/oauth-service"
    "shopno-platform/gateway" "shopno-platform/api-service" "shopno-platform/tenant-router"
    "shopno-platform/web-portal" "shopno-platform/domain-service" "shopno-platform/scheduler-service"
    "shopno-platform/notification-service" "shopno-platform/license-service"
    "shopno-monitoring/prometheus" "shopno-monitoring/grafana" "shopno-monitoring/loki"
    "shopno-monitoring/alertmanager"
    "shopno-payments/payment-service" "shopno-payments/exchange-service" "shopno-payments/billing-engine"
  )
  for d in "${order[@]}"; do
    local ns="${d%/*}"; local name="${d#*/}"
    kctl get deploy "$name" -n "$ns" >/dev/null 2>&1 || continue
    info "  restart $ns/$name"
    kctl rollout restart deploy "$name" -n "$ns" 2>/dev/null || true
  done
  ok "Restart wave issued"
}

# ─── PHASE 6 ────────────────────────────────────────────────────────────────
p6_verify() {
  hdr "PHASE 6 · Verify (up to 6 min for Tier-0)"
  local deadline=$((SECONDS + 360))
  while [[ $SECONDS -lt $deadline ]]; do
    local bad=0
    for d in "${TIER0[@]}"; do
      local ns="${d%/*}"; local name="${d#*/}"
      kctl get deploy "$name" -n "$ns" >/dev/null 2>&1 || continue
      local rdy
      rdy=$(kubectl get deploy "$name" -n "$ns" \
              -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
      [[ ${rdy:-0} -lt 1 ]] && bad=$((bad+1))
    done
    local running
    running=$(kubectl get pods -A --no-headers 2>/dev/null \
               | awk '$3=="Running"' | wc -l)
    echo "  [$(ts)] Running=$running not-ready-Tier0=$bad" | tee -a "$LOG_FILE"
    [[ $bad -eq 0 ]] && { ok "All Tier-0 Ready"; break; }
    sleep 15
  done
  info "Final snapshot:"
  kctl get pods -A \
    -o custom-columns=NS:.metadata.namespace,NAME:.metadata.name,\
READY:.status.containerStatuses[0].ready,STATUS:.status.phase,\
RESTARTS:.status.containerStatuses[0].restartCount,AGE:.metadata.creationTimestamp 2>/dev/null \
    | head -60
}

# ─── CLI ────────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)  DRY_RUN=true; shift ;;
    --phases)   SELECTED_PHASES="$2"; shift 2 ;;
    --log-dir)  LOG_DIR="$2"; shift 2 ;;
    -h|--help)  sed -n '2,18p' "$0"; exit 0 ;;
    *)          warn "unknown arg: $1"; exit 1 ;;
  esac
done

echo
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  shopnoltd cluster auto-recovery  (v2 — bash-safe)        ║"
echo "║  log : $LOG_FILE"
echo "║  mode: $($DRY_RUN && echo DRY-RUN || echo LIVE)   phases: $SELECTED_PHASES"
echo "╚═══════════════════════════════════════════════════════════╝"

phase_active 0 && p0_diagnose
phase_active 1 && p1_evict
phase_active 2 && p2_fix_config
phase_active 3 && p3_resize
phase_active 4 && p4_prioritise
phase_active 5 && p5_restart
phase_active 6 && p6_verify

echo
echo "Done. Log: $LOG_FILE"
echo "Re-enable apps one-at-a-time, watching the node pressure:"
echo "  kubectl describe node desktop-control-plane | grep -A 6 'Allocated resources'"
echo "  kubectl scale deploy jitsi-web -n shopno-apps --replicas=1"
