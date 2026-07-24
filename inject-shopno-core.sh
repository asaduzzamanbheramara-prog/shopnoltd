#!/usr/bin/env bash
# inject-shopno-core.sh
# Workaround: add a ConfigMap-based shopno_core to every Deployment that needs it.
# This gets the pods Running so we can see REAL errors instead of the
# import error masking everything else.
set -uo pipefail
shopt -s lastpipe
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
cd /mnt/c/Users/asadu/PROJECTS/shopnoltd

banner() { printf '\n\033[1;33m═══ %s ═══\033[0m\n' "$*"; }
ok()     { printf '\033[0;32m[OK]\033[0m %s\n' "$*"; }
warn()   { printf '\033[0;31m[WARN]\033[0m %s\n' "$*" >&2; }
info()   { printf '\033[0;36m[INFO]\033[0m %s\n' "$*"; }

# Phase 0: find all the affected services
banner "PHASE 0 · Find services with shopno_core import error"
AFFECTED=()
while read -r ns pod; do
  if kubectl logs "$pod" -n "$ns" --tail=30 --previous=true 2>/dev/null \
     | grep -qE "ModuleNotFoundError: No module named 'shopno_core'"; then
    deploy=$(echo "$pod" | sed -E 's/-[a-z0-9]+-[a-z0-9]+$//')
    AFFECTED+=("$ns/$deploy")
  fi
done < <(kubectl get pods -A --no-headers | grep "CrashLoopBackOff" | awk '{print $1, $2}')

if [[ ${#AFFECTED[@]} -eq 0 ]]; then
  info "no shopno_core errors detected in current CrashLoopBackOff pods"
  info "(they may be new pods that haven't logged yet — check the previous container)"
  info "trying PREVIOUS container logs too..."
  for ns in shopno-identity shopno-platform shopno-data shopno-apps shopno-payments; do
    for d in $(kubectl get deploy -n "$ns" -o name 2>/dev/null | sed 's|deployment.apps/||'); do
      # check if any pod owned by this deployment was in CrashLoopBackOff recently
      if kubectl get pods -n "$ns" -l "app.kubernetes.io/name=$d" --no-headers 2>/dev/null \
         | awk '$4=="CrashLoopBackOff" {exit 0} END{exit 1}'; then
        AFFECTED+=("$ns/$d")
      fi
    done
  done
fi

if [[ ${#AFFECTED[@]} -eq 0 ]]; then
  warn "still no shopno_core errors found. Run manually:"
  echo "  kubectl logs -n shopno-identity <pod> --previous"
  exit 1
fi
info "Affected services: ${#AFFECTED[@]}"
printf '  %s\n' "${AFFECTED[@]}"

# Phase 1: create the shopno_core ConfigMap
banner "PHASE 1 · Create shopno_core ConfigMap in each affected namespace"
for ns in $(printf '%s\n' "${AFFECTED[@]}" | cut -d/ -f1 | sort -u); do
  kubectl create configmap shopno-core-inject -n "$ns" \
    --from-literal=__init__.py="# shopnoltd placeholder" \
    --from-literal=database___init__.py="# shopnoltd placeholder" \
    --from-literal=database_redis.py="class RedisClient:
    def __init__(self, *a, **k): pass
redis_client = RedisClient()" \
    --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  ok "  $ns: ConfigMap shopno-core-inject created"
done

# Phase 2: patch each deployment
banner "PHASE 2 · Patch deployments to mount shopno_core"
for svc in "${AFFECTED[@]}"; do
  ns="${svc%/*}"; d="${svc#*/}"
  info "  $ns/$d"
  # Add volume + volumeMount + initContainer that extracts the ConfigMap
  kubectl patch deploy "$d" -n "$ns" --type=json -p='[
    {"op":"add","path":"/spec/template/spec/volumes/-",
     "value":{"name":"shopno-core","configMap":{"name":"shopno-core-inject"}}},
    {"op":"add","path":"/spec/template/spec/initContainers",
     "value":[
       {"name":"inject-shopno-core",
        "image":"busybox:1.36",
        "command":["/bin/sh","-c",
         "set -eu; \
          mkdir -p /app/shopno_core; \
          cp /shopno-core/__init__.py /app/shopno_core/__init__.py; \
          mkdir -p /app/shopno_core/database; \
          cp /shopno-core/database___init__.py /app/shopno_core/database/__init__.py; \
          cp /shopno-core/database_redis.py /app/shopno_core/database/redis.py; \
          echo injected"
        ],
        "volumeMounts":[
          {"name":"shopno-core","mountPath":"/shopno-core"},
          {"name":"shopno-core","mountPath":"/app/shopno_core","subPath":""}
        ]}
     ]}
  ]' >/dev/null 2>&1 && ok "    patched" || warn "    patch failed"

  # Add a volumeMount on the main container so /app/shopno_core is shared
  kubectl patch deploy "$d" -n "$ns" --type=json -p='[
    {"op":"add","path":"/spec/template/spec/containers/0/volumeMounts/-",
     "value":{"name":"shopno-core","mountPath":"/app/shopno_core"}}
  ]' >/dev/null 2>&1 || true
done

# Phase 3: restart CrashLoopBackOff pods
banner "PHASE 3 · Restart pods"
kubectl get pods -A --no-headers | grep "CrashLoopBackOff" | awk '{print $1, $2}' \
  | while read -r ns pod; do
      kubectl delete pod "$pod" -n "$ns" --grace-period=0 --force 2>/dev/null || true
    done
ok "pods deleted; replicasets will create fresh ones with the initContainer"

# Phase 4: wait + verify
banner "PHASE 4 · Wait and verify"
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
echo
echo "Breakdown of remaining errors:"
kubectl get pods -A --no-headers 2>/dev/null | grep -vE " Running | Completed " \
  | awk '{print $4}' | sort | uniq -c | sort -rn
