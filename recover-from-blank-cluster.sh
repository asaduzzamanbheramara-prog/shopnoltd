#!/usr/bin/env bash
# recover-from-blank-cluster.sh
# Apply your existing shopnoltd kustomize manifests in dependency order
# against the freshly-created kind-desktop cluster, then re-apply the
# 3 known patches from the previous recovery session.
set -euo pipefail
shopt -s lastpipe

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ─── CONFIG ────────────────────────────────────────────────────────────────
TIER0_NS=("shopno-data" "shopno-ingress")
TIER1_NS=("shopno-identity" "shopno-platform" "shopno-monitoring")
TIER2_NS=("shopno-payments")
TIER3_NS=("shopno-apps")

# Each tier pauses this long so pressure can settle before the next tier
TIER_PAUSE=( 20 25 25 25 )

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
    kubectl describe node "$n" 2>/dev/null \
      | awk '/Allocated resources:/{flag=1;next} flag && /^$/{flag=0} flag' \
      | head -8 \
      | sed "s/^/  $n  /"
  done
}

apply_kustomize() {
  local path="$1"
  if [[ -f "$path/kustomization.yaml" || -f "$path/Kustomization" ]]; then
    info "  kustomize: $path"
    k apply -k "$path" 2>&1 | sed 's/^/    /' || warn "  failed: $path"
  elif ls "$path"/*.yaml >/dev/null 2>&1; then
    info "  raw files: $path"
    k apply -f "$path" 2>&1 | sed 's/^/    /' || warn "  failed: $path"
  else
    warn "  nothing to apply in $path"
  fi
}

# ─── PHASE 0: DIAGNOSTICS ──────────────────────────────────────────────────
banner "PHASE 0 · Diagnostics"
info "context: $(kubectl config current-context)"
kubectl get nodes -o custom-columns=NAME:.metadata.name,ROLES:.metadata.labels,\
CPU:.status.allocatable.cpu,MEM:.status.allocatable.memory
info "storage classes:"
kubectl get sc
info "cluster pressure (should be near 0):"
pressure

# ─── PHASE 1: NAMESPACES ───────────────────────────────────────────────────
banner "PHASE 1 · Namespaces"
if [[ -d k8s/namespaces ]]; then
  k apply -f k8s/namespaces/
  ok "k8s/namespaces/ applied"
else
  warn "k8s/namespaces/ missing — using kustomize-only mode"
fi

# also pick up any namespace.yaml that lives under services/ (yours do)
while read -r f; do
  info "  $f"
  k apply -f "$f"
done < <(find k8s/services -maxdepth 2 -name namespace.yaml 2>/dev/null | sort)

# ─── PHASE 2: BASE (kustomize) ──────────────────────────────────────────────
banner "PHASE 2 · Base kustomization (RBAC, network policies, common config)"
if [[ -f k8s/base/kustomization.yaml ]]; then
  apply_kustomize k8s/base
elif [[ -f k8s/kustomization.yaml && ! -d k8s/base ]]; then
  apply_kustomize k8s
else
  warn "no kustomization.yaml found in k8s/ or k8s/base/ — skipping"
fi

# ─── PHASE 3: TIERED SERVICES ──────────────────────────────────────────────
banner "PHASE 3 · Apply services in tiers"

apply_tier() {
  local ns="$1"; local pause="$2"
  banner "Tier: $ns"
  # 1) k8s/services/<ns-or-name>/* if present
  for cand in "k8s/services/$ns" "platform/$ns/k8s" "apps/$ns/k8s"; do
    if [[ -d "$cand" ]]; then
      apply_kustomize "$cand"
    fi
  done
  # 2) any kustomize bundle named after the tier member
  for d in k8s/services/*/; do
    [[ -z "$d" ]] && continue
    case "$(basename "$d")" in
      "$ns"|"${ns#shopno-}"|"${ns%-*}")
        apply_kustomize "${d%/}"
        ;;
    esac
  done
  if ! $DRY_RUN; then
    info "  pressure after $ns:"
    pressure
    info "  sleeping ${pause}s for pods to settle…"
    sleep "$pause"
  fi
}

apply_tier shopno-data            "${TIER_PAUSE[0]}"
apply_tier shopno-identity        "${TIER_PAUSE[1]}"
apply_tier shopno-platform        "${TIER_PAUSE[2]}"
apply_tier shopno-monitoring      "${TIER_PAUSE[2]}"
apply_tier shopno-payments        "${TIER_PAUSE[3]}"

# Tier-4 (shopno-apps) is opt-in — many are heavy (jitsi×4, chatwoot, mailcow…)
banner "Tier-4 (shopno-apps) — interactive"
read -rp "Apply shopno-apps/* now? [y/N] " ans
if [[ "${ans,,}" == "y" ]]; then
  apply_tier shopno-apps 30
fi

# ─── PHASE 4: KNOWN PATCHES ────────────────────────────────────────────────
banner "PHASE 4 · Apply known patches"

# 4a) billing-engine — PodSecurity restricted
if kubectl get deploy billing-engine -n shopno-payments >/dev/null 2>&1; then
  info "  billing-engine: restricted securityContext"
  kubectl -n shopno-payments patch deploy billing-engine --type=json -p='[
    {"op":"add","path":"/spec/template/spec/securityContext",
     "value":{"runAsNonRoot":true,"seccompProfile":{"type":"RuntimeDefault"}}},
    {"op":"add","path":"/spec/template/spec/containers/0/securityContext",
     "value":{"allowPrivilegeEscalation":false,
              "capabilities":{"drop":["ALL"]},
              "runAsNonRoot":true,
              "seccompProfile":{"type":"RuntimeDefault"}}}]' 2>&1 | tail -1 \
    || warn "  (patch may already be applied)"
else
  warn "  billing-engine not present — skipped"
fi

# 4b) chatwoot — pin tag, drop :latest
if kubectl get deploy chatwoot -n shopno-apps >/dev/null 2>&1; then
  info "  chatwoot: pin image (no :latest)"
  for img in "chatwoot/chatwoot-web:v3.13.0" "chatwoot/chatwoot-web:v3.0"; do
    if kubectl -n shopno-apps set image deploy/chatwoot "chatwoot=$img" \
         2>/dev/null | grep -q "image updated"; then
      ok "  chatwoot → $img"; break
    fi
  done
else
  warn "  chatwoot not present — skipped"
fi

# 4c) mail-server — drop redundant init
if kubectl get deploy mail-server -n default >/dev/null 2>&1; then
  info "  mail-server: drop init container"
  kubectl -n default patch deploy mail-server --type=json \
    -p='[{"op":"remove","path":"/spec/template/spec/initContainers"}]' \
    2>/dev/null || warn "  (init already removed)"
  kubectl -n default delete pods -l app=mail-server \
    --grace-period=0 --force 2>/dev/null || true
else
  warn "  mail-server not present — skipped"
fi

# 4d) Pending PVCs → local-path (in case SC was wrong)
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

# ─── PHASE 5: VERIFY ────────────────────────────────────────────────────────
banner "PHASE 5 · Verify (up to 6 min)"
if ! $DRY_RUN; then
  for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
    bad=$(kubectl get pods -A --no-headers 2>/dev/null \
          | awk '$3!="Running" && $3!="Completed"' | wc -l)
    total=$(kubectl get pods -A --no-headers 2>/dev/null | wc -l)
    running=$(kubectl get pods -A --no-headers 2>/dev/null \
              | awk '$3=="Running"' | wc -l)
    echo "  [t+${i}*30s] pods=$total running=$running not-ok=$bad" \
      | tee -a /tmp/shopnoltd-recovery/last-verify.log
    kubectl get pods -A -o custom-columns=\
NS:.metadata.namespace,NAME:.metadata.name,\
READY:.status.containerStatuses[0].ready,STATUS:.status.phase,\
RESTARTS:.status.containerStatuses[0].restartCount 2>/dev/null \
      | grep -vE " Running | Completed " | head -25
    [[ $bad -eq 0 ]] && { ok "All pods Running/Completed"; break; }
    sleep 30
  done
fi

ok "Recovery complete."
echo
echo "  Pressure:"
pressure
echo
echo "  Useful next steps:"
echo "    kubectl get pods -A | grep -vE ' Running | Completed '"
echo "    kubectl get events -A --field-selector reason=FailedScheduling --sort-by=.lastTimestamp | tail -10"
echo "    kubectl logs -n shopno-data deploy/postgres --tail=20    # if it won't start"
