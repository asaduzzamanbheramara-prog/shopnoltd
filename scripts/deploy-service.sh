#!/usr/bin/env bash
# Deploy one service with a safety net: if the rollout doesn't go healthy,
# print a concrete diagnosis and (optionally) roll back to the last known
# good revision automatically.
#
# Usage:
#   ./scripts/deploy-service.sh <service> [--auto-rollback] [--timeout 180s]
#
# Examples:
#   ./scripts/deploy-service.sh oauth-service --auto-rollback
#   ./scripts/deploy-service.sh keycloak
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SERVICE="${1:-}"
[ -z "$SERVICE" ] && { echo "Usage: $0 <service> [--auto-rollback] [--timeout 180s]"; exit 2; }
shift

AUTO_ROLLBACK=0
TIMEOUT="180s"
while [ $# -gt 0 ]; do
  case "$1" in
    --auto-rollback) AUTO_ROLLBACK=1 ;;
    --timeout) TIMEOUT="$2"; shift ;;
  esac
  shift
done

DIR="k8s/services/$SERVICE"
[ -d "$DIR" ] || { echo "No such service: $SERVICE (looked in $DIR)"; exit 2; }

NAMESPACE="$(grep -m1 '^namespace:' "$DIR/kustomization.yaml" | awk '{print $2}')"
NAMESPACE="${NAMESPACE:-default}"
LOG_DIR=".deploy-history/$SERVICE"
mkdir -p "$LOG_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

echo "==> Preflight check for $SERVICE"
if ! ./scripts/preflight-check.sh "$SERVICE"; then
  echo "==> Aborting: fix preflight problems first (see above)."
  exit 1
fi

echo "==> Recording current revision (for rollback / history) before applying"
kubectl rollout history "deployment/$SERVICE" -n "$NAMESPACE" > "$LOG_DIR/pre-deploy-history-$STAMP.txt" 2>&1 || true

echo "==> Applying $DIR"
if ! kubectl apply -k "$DIR" 2>&1 | tee "$LOG_DIR/apply-$STAMP.log"; then
  echo
  echo "==> kubectl apply itself failed (didn't even reach the cluster rollout stage)."
  echo "    Most common causes:"
  echo "    - not connected to the right cluster: check 'kubectl config current-context'"
  echo "    - a CRD this manifest needs isn't installed yet (e.g. ServiceMonitor needs"
  echo "      the Prometheus Operator: scripts/install-prometheus-operator.sh)"
  echo "    - YAML syntax error: run 'kubectl kustomize $DIR' to see the rendered output"
  exit 1
fi

echo "==> Waiting for rollout (timeout $TIMEOUT)"
if kubectl rollout status "deployment/$SERVICE" -n "$NAMESPACE" --timeout="$TIMEOUT" 2>&1 | tee "$LOG_DIR/rollout-$STAMP.log"; then
  echo "==> $SERVICE deployed successfully."
  echo "success" >> "$LOG_DIR/outcomes.log"
  exit 0
fi

echo
echo "############################################################"
echo "  ROLLOUT FAILED for $SERVICE -- diagnosing"
echo "############################################################"
echo "failed $STAMP" >> "$LOG_DIR/outcomes.log"

{
  echo "--- kubectl get pods ---"
  kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/name=$SERVICE" 2>&1
  echo
  echo "--- kubectl describe pod (most recent) ---"
  POD="$(kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/name=$SERVICE" --sort-by=.metadata.creationTimestamp -o name 2>/dev/null | tail -1)"
  [ -n "$POD" ] && kubectl describe "$POD" -n "$NAMESPACE" 2>&1
  echo
  echo "--- kubectl logs (current + previous container, last 100 lines) ---"
  if [ -n "$POD" ]; then
    kubectl logs "$POD" -n "$NAMESPACE" --tail=100 2>&1
    echo "--- previous container (if it crashed and restarted) ---"
    kubectl logs "$POD" -n "$NAMESPACE" --previous --tail=100 2>&1 || echo "(no previous container log)"
  fi
  echo
  echo "--- recent events ---"
  kubectl get events -n "$NAMESPACE" --sort-by=.lastTimestamp 2>&1 | tail -20
} | tee "$LOG_DIR/diagnosis-$STAMP.log"

echo
echo "==> Likely cause, based on the above:"
DIAG_FILE="$LOG_DIR/diagnosis-$STAMP.log"
if grep -qi "ImagePullBackOff\|ErrImagePull" "$DIAG_FILE"; then
  echo "    IMAGE PULL FAILURE -- the image tag in deployment.yaml doesn't exist"
  echo "    or the registry needs auth. Check the 'image:' line and whether"
  echo "    the GitHub Actions build pipeline actually pushed that tag to ghcr.io."
elif grep -qi "CrashLoopBackOff" "$DIAG_FILE"; then
  echo "    CONTAINER IS CRASHING ON STARTUP -- check the logs above for a stack"
  echo "    trace. Common cause here: a secret.yaml key is still REPLACE_WITH_BASE64"
  echo "    (re-run scripts/preflight-check.sh $SERVICE), or a DB/Redis hostname"
  echo "    in configmap.yaml doesn't match where that dependency actually runs."
elif grep -qi "OOMKilled" "$DIAG_FILE"; then
  echo "    OUT OF MEMORY -- raise the memory limit in deployment.yaml resources.limits.memory."
elif grep -qi "readiness probe failed\|liveness probe failed" "$DIAG_FILE"; then
  echo "    HEALTH CHECK FAILING -- the app started but isn't answering its"
  echo "    /healthz or /readyz path yet. Check the logs above for what's blocking"
  echo "    startup (commonly: can't reach Postgres/Redis)."
elif grep -qi "FailedScheduling" "$DIAG_FILE"; then
  echo "    CAN'T BE SCHEDULED -- check node resources / topologySpreadConstraints"
  echo "    in the events above."
else
  echo "    Not one of the common patterns -- read the diagnosis log above, or"
  echo "    open $DIAG_FILE"
fi

if [ "$AUTO_ROLLBACK" -eq 1 ]; then
  echo
  echo "==> --auto-rollback set: rolling back to the last known-good revision"
  if kubectl rollout undo "deployment/$SERVICE" -n "$NAMESPACE" 2>&1 | tee "$LOG_DIR/rollback-$STAMP.log"; then
    kubectl rollout status "deployment/$SERVICE" -n "$NAMESPACE" --timeout="$TIMEOUT"
    echo "==> Rolled back successfully. $SERVICE is back on its previous working revision."
    echo "    The broken manifest is still on disk -- fix the cause above before re-applying."
  else
    echo "==> Rollback itself failed. This needs a human: 'kubectl rollout history deployment/$SERVICE -n $NAMESPACE'"
    exit 1
  fi
else
  echo
  echo "==> Not rolling back automatically (pass --auto-rollback to do this next time)."
  echo "    To roll back manually right now:"
  echo "      kubectl rollout undo deployment/$SERVICE -n $NAMESPACE"
fi

exit 1
