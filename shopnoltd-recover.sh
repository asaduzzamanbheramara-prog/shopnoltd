#!/usr/bin/env bash
###############################################################################
# shopnoltd-recover.sh
# Auto-remediation for the resource-starved kind cluster.
#
# Phases:
#   0  Diagnostics          (read-only)
#   1  Evict stuck pods     (force-delete Terminating pods, free capacity)
#   2  Fix config bugs      (PodSecurity, image, PVC storage class)
#   3  Right-size requests  (drop 100m→50m, 512Mi→256Mi for single node)
#   4  Prioritise workloads (scale optional to 0, pin critical to 1)
#   5  Rolling restart      (in dependency order, infra → apps)
#   6  Verify               (wait until critical pods are Ready)
#
# Usage:
#   chmod +x shopnoltd-recover.sh
#   ./shopnoltd-recover.sh                  # full recovery
#   ./shopnoltd-recover.sh --dry-run         # preview
#   ./shopnoltd-recover.sh --phases 0,1,2    # run specific phases
#   ./shopnoltd-recover.sh --phases 4,5,6    # restart in order
###############################################################################
set -euo pipefail

# ─── CONFIG (tweak to taste) ────────────────────────────────────────────────
LOG_DIR="${LOG_DIR:-/tmp/shopnoltd-recovery}"
DRY_RUN=false
SELECTED_PHASES="0,1,2,3,4,5,6"

# Tier-0 : must stay up (1 replica)
TIER0=(
  "shopno-data/postgres" "shopno-data/redis" "shopno-data/minio" "shopno-data/opensearch"
  "shopno-identity/keycloak" "shopno-identity/auth-service" "shopno-identity/oauth-service"
  "shopno-platform/gateway" "shopno-platform/web-portal" "shopno-platform/tenant-router"
  "shopno-platform/api-service" "shopno-monitoring/prometheus" "shopno-monitoring/grafana"
  "ingress-nginx/ingress-nginx-controller"
)
# Tier-3 : scale to 0 (re-enable with --bring-up later)
TIER3=(
  "shopno-apps/jitsi-web" "shopno-apps/jitsi-jicofo" "shopno-apps/jitsi-jvb" "shopno-apps/jitsi-prosody"
  "shopno-apps/chatwoot" "shopno-apps/code-server" "shopno-apps/owncast"
  "shopno-apps/nextcloud" "shopno-apps/onlyoffice"
  "shopno-apps/n8n" "shopno-apps/metabase" "shopno-apps/superset" "shopno-apps/kobotoolbox" "shopno-apps/gitea"
  "shopno-payments/billing-engine"
)
# Single-node-friendly resource profile
CPU_REQ=50m;  CPU_LIM=300m
MEM_REQ=64Mi; MEM_LIM=256Mi
EPH_REQ=128Mi;EPH_LIM=512Mi

# ─── BOOTSTRAP ──────────────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/recover-$(date +%Y%m%d-%H%M%S).log"
if [[ -t 1 ]]; then
  RED=$'\033[0;31m'; GRN=$'\033[0;32m'; YLW=$'\033[1;33m'; CYN=$'\033[0;36m'; NC=$'\033[0m'
else RED=''; GRN=''; YLW=''; CYN=''; NC=''; fi

ts()  { date '+%H:%M:%S'; }
log() { echo -e "$(ts) ${CYN}[$1]${NC} $2" | tee -a "$LOG_FILE"; }
info(){ log "INFO" "$1"; }
warn(){ log "WARN" "$1" >&2; }
ok()  { log "OK"   "$1"; }
hdr() { echo -e "\n${YLW}═══ $* ═══${NC}" | tee -a "$LOG_FILE"; }

kctl() {                              # dry-run aware kubectl
  if $DRY_RUN; then echo "  [DRY-RUN] kubectl $*" | tee -a "$LOG_FILE"
  else kubectl "$@"; fi
}
phase_active() { [[ ",$SELECTED_PHASES," == *",$1,"* ]]; }

# ─── PHASE 0: DIAGNOSTICS ───────────────────────────────────────────────────
p0_diagnose() {
  hdr "PHASE 0 · Diagnostics"
  info "Nodes:"
  kctl get nodes -o custom-columns=\
NAME:.metadata.name,STATUS:.status.conditions[?(@.type=='Ready')].status,\
CPU:.status.allocatable.cpu,MEM:.status.allocatable.memory,\
PODS:.status.allocatable.pods
  info "Storage classes:"
  kctl get sc
  info "Pod status counts:"
  for s in Running Pending CrashLoopBackOff ImagePullBackOff Terminating Error Init; do
    n=$(kubectl get pods -A --no-headers 2>/dev/null | grep -cE " $s( |$)" || true)
    [[ $n -gt 0 ]] && warn "  $s: $n"
  done
  info "Top failing workloads:"
  kubectl get pods -A --no-headers 2>/dev/null \
    | grep -vE " Running | Completed " \
    | awk '{print $2}' | sed -E 's/-[a-z0-9]+-[a-z0-9]+$//' \
    | sort | uniq -c | sort -rn | head -10
  info "Recent FailedScheduling events:"
  kubectl get events -A --field-selector reason=FailedScheduling \
    --sort-by=.lastTimestamp 2>/dev/null | tail -5 || true
}

# ─── PHASE 1: EVICT STUCK PODS ──────────────────────────────────────────────
p1_evict() {
  hdr "PHASE 1 · Force-evict stuck Terminating pods"

  # 1a) Anything in Terminating state
  mapfile -t stuck < <(kubectl get pods -A --field-selector=status.phase=Terminating \
                       --no-headers 2>/dev/null | awk '{print $1" "$2}')
  # 1b) Pending pods older than 2 min that have no scheduled node
  mapfile -t pending_old < <(kubectl get pods -A --no-headers 2>/dev/null \
    | awk '$3=="0/1" && $4=="Pending" {print $1" "$2}')

  local total=0
  for line in "${stuck[@]:-}" "${pending_old[@]:-}"; do
    [[ -z "$line" ]] && continue
    local ns="${line%% *}"; local pod="${line##* }"
    info "  evict $ns/$pod"
    kctl delete pod "$pod" -n "$ns" --grace-period=0 --force 2>/dev/null \
      || warn "  already gone: $pod"
    total=$((total+1))
  done
  ok "Evicted $total stuck/old pods"

  info "Cleaning up orphaned ReplicaSets with 0 desired but live pods..."
  kubectl get rs -A --no-headers 2>/dev/null \
    | awk '$3==0 && $4>0 {print $1" "$2}' | while read -r ns rs; do
    [[ -z "$ns" ]] && continue
    info "  deleting orphaned RS $ns/$rs"
    kctl delete rs "$rs" -n "$ns" 2>/dev/null || true
  done
}

# ─── PHASE 2: FIX CONFIG ────────────────────────────────────────────────────
p2_fix_config() {
  hdr "PHASE 2 · Fix configuration issues"

  # 2a) billing-engine — add restricted-PodSecurity-compliant securityContext
  if kctl get deploy billing-engine -n shopno-payments >/dev/null 2>&1; then
    info "Patching billing-engine securityContext (restricted)..."
    kctl patch deploy billing-engine -n shopno-payments --type=json -p='[
      {"op":"add","path":"/spec/template/spec/securityContext",
       "value":{"runAsNonRoot":true,"seccompProfile":{"type":"RuntimeDefault"}}},
      {"op":"add","path":"/spec/template/spec/containers/0/securityContext",
       "value":{"allowPrivilegeEscalation":false,
                "capabilities":{"drop":["ALL"]},
                "runAsNonRoot":true,"seccompProfile":{"type":"RuntimeDefault"}}}
    ]' 2>&1 | tail -1 || warn "billing-engine patch may already be applied"
  fi

  # 2b) chatwoot — pin a specific image tag (avoids :latest rate-limit/auth issues)
  if kctl get deploy chatwoot -n shopno-apps >/dev/null 2>&1; then
    info "Pinning chatwoot image to a known-published tag..."
    for img in \
        "chatwoot/chatwoot-web:v3.13.0" \
        "chatwoot/chatwoot-web:v3.0" \
        "ghcr.io/chatwoot/chatwoot/chatwoot-web:latest"; do
      if kctl set image deploy/chatwoot -n shopno-apps "chatwoot=$img" 2>/dev/null | grep -q "image updated"; then
        ok "  chatwoot image → $img"; break
      fi
    done
    # If none worked, leave it but warn
    kctl get deploy chatwoot -n shopno-apps \
      -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null \
      | { read -r cur; info "  current chatwoot image: $cur"; }
  fi

  # 2c) mail-server — the init container chmod 1777 /dev/shm blocks startup;
  #     main container already runs as root, so the init is redundant.
  if kctl get deploy mail-server -n default >/dev/null 2>&1; then
    info "Removing mail-server init container (redundant with root main)..."
    kctl patch deploy mail-server -n default --type=json -p='[
      {"op":"remove","path":"/spec/template/spec/initContainers"}
    ]' 2>/dev/null || warn "  init container may already be absent"
    kctl delete pods -n default -l app=mail-server \
      --grace-period=0 --force 2>/dev/null || true
  fi

  # 2d) Pending PVCs — switch from `standard` to `local-path` (kind's provisioner)
  info "Re-binding Pending PVCs to local-path storage class..."
  kubectl get pvc -A --no-headers 2>/dev/null \
    | awk '$3=="Pending" {print $1" "$2}' | while read -r ns pvc; do
    [[ -z "$ns" ]] && continue
    info "  $ns/$pvc"
    kctl patch pvc "$pvc" -n "$ns" --type=json -p='[
      {"op":"replace","path":"/spec/storageClassName","value":"local-path"}
    ]' 2>/dev/null \
      || warn "    patch failed, manual recreate needed"
  done
}

# ─── PHASE 3: RIGHT-SIZE REQUESTS ───────────────────────────────────────────
p3_resize() {
  hdr "PHASE 3 · Right-size resource requests (single-node friendly)"
  local patched=0
  for d in "${TIER0[@]}" "${TIER3[@]}"; do
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
  ok "Right-sized $patched deployments ($CPU_REQ/$CPU_LIM CPU, $MEM_REQ/$MEM_LIM mem)"
}

# ─── PHASE 4: PRIORITISE ────────────────────────────────────────────────────
p4_prioritise() {
  hdr "PHASE 4 · Prioritise workloads"
  info "Scaling Tier-3 (optional) workloads to 0..."
  for d in "${TIER3[@]}"; do
    local ns="${d%/*}"; local name="${d#*/}"
    kctl get deploy "$name" -n "$ns" >/dev/null 2>&1 || continue
    kctl scale deploy "$name" -n "$ns" --replicas=0 2>/dev/null || true
  done
  info "Ensuring Tier-0 (critical) is 1 replica..."
  for d in "${TIER0[@]}"; do
    local ns="${d%/*}"; local name="${d#*/}"
    kctl get deploy "$name" -n "$ns" >/dev/null 2>&1 || continue
    kctl scale deploy "$name" -n "$ns" --replicas=1 2>/dev/null || true
  done
  ok "Prioritisation done"
}

# ─── PHASE 5: ROLLING RESTART IN ORDER ──────────────────────────────────────
p5_restart() {
  hdr "PHASE 5 · Rolling restart in dependency order"
  local order=(
    # L1  storage
    "shopno-data/postgres" "shopno-data/redis" "shopno-data/minio" "shopno-data/opensearch"
    # L2  identity
    "shopno-identity/keycloak" "shopno-identity/auth-service" "shopno-identity/oauth-service"
    # L3  platform
    "shopno-platform/gateway" "shopno-platform/api-service" "shopno-platform/tenant-router"
    "shopno-platform/web-portal" "shopno-platform/domain-service" "shopno-platform/scheduler-service"
    "shopno-platform/notification-service" "shopno-platform/license-service"
    # L4  monitoring
    "shopno-monitoring/prometheus" "shopno-monitoring/grafana" "shopno-monitoring/loki"
    "shopno-monitoring/alertmanager"
    # L5  payments
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

# ─── PHASE 6: VERIFY ────────────────────────────────────────────────────────
p6_verify() {
  hdr "PHASE 6 · Verify recovery"
  info "Waiting up to 6 min for Tier-0 to become Ready..."
  local deadline=$((SECONDS + 360))
  while [[ $SECONDS -lt $deadline ]]; do
    local bad=0
    for d in "${TIER0[@]}"; do
      local ns="${d%/*}"; local name="${d#*/}"
      kctl get deploy "$name" -n "$ns" >/dev/null 2>&1 || continue
      local rdy
      rdy=$(kubectl get deploy "$name" -n "$ns" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
      [[ ${rdy:-0} -lt 1 ]] && bad=$((bad+1))
    done
    local rdy_count
    rdy_count=$(kubectl get pods -A --no-headers 2>/dev/null | grep -c " Running " || true)
    echo "  [$(ts)] total Running: $rdy_count | not-ready-Tier0: $bad" | tee -a "$LOG_FILE"
    [[ $bad -eq 0 ]] && { ok "All Tier-0 deployments Ready"; break; }
    sleep 15
  done
  info "Final snapshot:"
  kctl get pods -A -o custom-columns=\
NS:.metadata.namespace,NAME:.metadata.name,READY:.status.containerStatuses[0].ready,\
STATUS:.status.phase,RESTARTS:.status.containerStatuses[0].restartCount,AGE:.metadata.creationTimestamp \
    2>/dev/null | head -60
}

# ─── CLI ────────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)        DRY_RUN=true; shift ;;
    --phases)         SELECTED_PHASES="$2"; shift 2 ;;
    --log-dir)        LOG_DIR="$2"; shift 2 ;;
    -h|--help)        sed -n '2,20p' "$0"; exit 0 ;;
    *)                warn "unknown arg: $1"; exit 1 ;;
  esac
done

echo -e "${GRN}╔═══════════════════════════════════════════════════════════╗"
echo -e "║  shopnoltd cluster auto-recovery                          ║"
echo -e "║  log : $LOG_FILE"
echo -e "║  mode: $($DRY_RUN && echo DRY-RUN || echo LIVE)  phases: $SELECTED_PHASES"
echo -e "╚═══════════════════════════════════════════════════════════╝${NC}"

phase_active 0 && p0_diagnose
phase_active 1 && p1_evict
phase_active 2 && p2_fix_config
phase_active 3 && p3_resize
phase_active 4 && p4_prioritise
phase_active 5 && p5_restart
phase_active 6 && p6_verify

echo -e "\n${GRN}Done. Full log: $LOG_FILE${NC}"
echo -e "${YLW}To re-enable optional apps later:${NC}"
echo -e "  for d in jitsi-web jitsi-jicofo jitsi-jvb jitsi-prosody chatwoot code-server \\"
echo -e "           owncast nextcloud onlyoffice n8n metabase superset kobotoolbox gitea; do"
echo -e "    kubectl scale deploy \$d -n shopno-apps --replicas=1"
echo -e "  done"
echo -e "  kubectl scale deploy billing-engine -n shopno-payments --replicas=1"
