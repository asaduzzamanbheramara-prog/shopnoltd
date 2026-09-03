#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/mnt/c/Users/asadu/PROJECTS/shopnoltd"
REMOTE="origin"
BRANCH="main"
APP="shopnoltd"
ARGO_NS="argocd"

if [[ $# -gt 0 ]]; then
    UPDATE_FILES=("$@")
elif [[ -n "${SHOPNOLTD_UPDATE_FILES:-}" ]]; then
    read -r -a UPDATE_FILES <<< "$SHOPNOLTD_UPDATE_FILES"
else
    echo "ERROR: No update files supplied."
    echo
    echo "Usage:"
    echo "  ./shopnoltd-safe-update.sh path/to/file"
    echo "  ./shopnoltd-safe-update.sh file1 file2 file3"
    exit 1
fi

cd "$ROOT"

log() {
    echo
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

fail() {
    echo
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "FAILED: $1"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    exit 1
}

trap '[[ -n "${PF_PID:-}" ]] && kill "$PF_PID" 2>/dev/null || true' EXIT

log "1. CHECK LOCAL ENVIRONMENT"

command -v git >/dev/null || fail "git is not installed"
command -v kubectl >/dev/null || fail "kubectl is not installed"

[[ -d "$ROOT/.git" ]] || fail "Not a Git repository: $ROOT"

CURRENT_BRANCH="$(git branch --show-current)"
[[ "$CURRENT_BRANCH" == "$BRANCH" ]] ||
    fail "Current branch is '$CURRENT_BRANCH', expected '$BRANCH'"

echo "Project: $ROOT"
echo "Branch : $BRANCH"
echo "ArgoCD : $APP"

log "2. CHECK WORKING TREE"

mapfile -t STATUS_LINES < <(git status --porcelain)

if [[ ${#STATUS_LINES[@]} -gt 0 ]]; then
    echo "Existing working-tree changes:"
    printf '  %s\n' "${STATUS_LINES[@]}"
else
    echo "Working tree is clean."
fi

declare -A ALLOWED=()

for f in "${UPDATE_FILES[@]}"; do
    f="${f#./}"

    [[ -e "$f" || -L "$f" ]] ||
        fail "Update file does not exist: $f"

    ALLOWED["$f"]=1
done

echo
echo "Intended update files:"
printf '  %s\n' "${!ALLOWED[@]}"

log "3. PROTECT UNRELATED LOCAL CHANGES"

UNRELATED=()

while IFS= read -r line; do
    [[ -z "$line" ]] && continue

    path="${line:3}"

    if [[ "$path" == *" -> "* ]]; then
        old="${path%% -> *}"
        new="${path##* -> }"

        [[ -n "${ALLOWED[$old]:-}" ]] ||
        [[ -n "${ALLOWED[$new]:-}" ]] ||
            UNRELATED+=("$path")
    else
        [[ -n "${ALLOWED[$path]:-}" ]] ||
            UNRELATED+=("$path")
    fi
done < <(git status --porcelain)

if [[ ${#UNRELATED[@]} -gt 0 ]]; then
    echo
    echo "STOP: unrelated local changes detected:"
    printf '  %s\n' "${UNRELATED[@]}"
    echo
    echo "Nothing will be staged, committed, pushed, or deployed."
    exit 2
fi

echo "No unrelated local changes detected."

log "4. CHECK INTENDED DIFF"

git diff -- "${UPDATE_FILES[@]}" || true
git diff --cached -- "${UPDATE_FILES[@]}" || true

git diff --check -- "${UPDATE_FILES[@]}" ||
    fail "Whitespace/error check failed"

log "5. CHECK GITHUB"

git fetch "$REMOTE" "$BRANCH"

LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse "$REMOTE/$BRANCH")"

echo "Local : $LOCAL_SHA"
echo "Remote: $REMOTE_SHA"

[[ "$LOCAL_SHA" == "$REMOTE_SHA" ]] ||
    fail "Local HEAD differs from origin/main. Resolve Git divergence first."

log "6. CHECK KUBERNETES"

kubectl cluster-info >/dev/null ||
    fail "Kubernetes cluster is unreachable"

kubectl get nodes -o wide

log "7. CHECK ARGOCD BEFORE UPDATE"

kubectl -n "$ARGO_NS" get application "$APP" \
    -o jsonpath='SYNC={.status.sync.status} HEALTH={.status.health.status} PHASE={.status.operationState.phase} REV={.status.sync.revision}{"\n"}' ||
    fail "ArgoCD Application '$APP' not found"

log "8. STAGE ONLY INTENDED FILES"

git reset >/dev/null 2>&1 || true

git add -- "${UPDATE_FILES[@]}"

git diff --cached --check ||
    fail "Staged diff check failed"

mapfile -t STAGED_FILES < <(git diff --cached --name-only)

for f in "${STAGED_FILES[@]}"; do
    [[ -n "${ALLOWED[$f]:-}" ]] ||
        fail "Unexpected staged file: $f"
done

[[ ${#STAGED_FILES[@]} -gt 0 ]] ||
    fail "Nothing staged."

echo
echo "Staged files:"
git diff --cached --name-status

log "9. FINAL STAGED DIFF"

git diff --cached --stat

echo
git diff --cached

echo
read -r -p "Proceed with commit and deployment? [yes/NO]: " ANSWER

[[ "$ANSWER" == "yes" ]] ||
    fail "Cancelled by user."

log "10. CREATE COMMIT"

read -r -p "Commit message: " COMMIT_MESSAGE

[[ -n "$COMMIT_MESSAGE" ]] ||
    fail "Commit message cannot be empty."

git commit -m "$COMMIT_MESSAGE"

NEW_SHA="$(git rev-parse HEAD)"

echo "New commit: $NEW_SHA"

log "11. PUSH TO GITHUB"

git push "$REMOTE" "$BRANCH"

PUSHED_SHA="$(git rev-parse "$REMOTE/$BRANCH")"

[[ "$NEW_SHA" == "$PUSHED_SHA" ]] ||
    fail "GitHub branch did not reach expected commit."

echo "GitHub main: $PUSHED_SHA"

log "12. WAIT FOR ARGOCD"

for i in $(seq 1 60); do
    REV="$(kubectl -n "$ARGO_NS" get application "$APP" \
        -o jsonpath='{.status.sync.revision}' 2>/dev/null || true)"

    SYNC="$(kubectl -n "$ARGO_NS" get application "$APP" \
        -o jsonpath='{.status.sync.status}' 2>/dev/null || true)"

    HEALTH="$(kubectl -n "$ARGO_NS" get application "$APP" \
        -o jsonpath='{.status.health.status}' 2>/dev/null || true)"

    PHASE="$(kubectl -n "$ARGO_NS" get application "$APP" \
        -o jsonpath='{.status.operationState.phase}' 2>/dev/null || true)"

    printf '[%02d/60] SYNC=%s HEALTH=%s PHASE=%s REV=%s\n' \
        "$i" "$SYNC" "$HEALTH" "$PHASE" "$REV"

    [[ "$REV" == "$NEW_SHA" ]] && break

    sleep 5
done

log "13. REQUEST ARG0CD SYNC IF NEEDED"

REV="$(kubectl -n "$ARGO_NS" get application "$APP" \
    -o jsonpath='{.status.sync.revision}' 2>/dev/null || true)"

if [[ "$REV" != "$NEW_SHA" ]]; then
    kubectl -n "$ARGO_NS" patch application "$APP" \
        --type=merge \
        -p '{"operation":{"sync":{"prune":false}}}' ||
        fail "Could not request ArgoCD sync."

    echo "ArgoCD sync requested."
else
    echo "ArgoCD already observed the new revision."
fi

log "14. WAIT FOR GITOPS DEPLOYMENT"

SUCCESS=0

for i in $(seq 1 120); do

    SYNC="$(kubectl -n "$ARGO_NS" get application "$APP" \
        -o jsonpath='{.status.sync.status}' 2>/dev/null || true)"

    HEALTH="$(kubectl -n "$ARGO_NS" get application "$APP" \
        -o jsonpath='{.status.health.status}' 2>/dev/null || true)"

    PHASE="$(kubectl -n "$ARGO_NS" get application "$APP" \
        -o jsonpath='{.status.operationState.phase}' 2>/dev/null || true)"

    REV="$(kubectl -n "$ARGO_NS" get application "$APP" \
        -o jsonpath='{.status.sync.revision}' 2>/dev/null || true)"

    printf '[%03d/120] SYNC=%s HEALTH=%s PHASE=%s REV=%s\n' \
        "$i" "$SYNC" "$HEALTH" "$PHASE" "$REV"

    if [[ "$REV" == "$NEW_SHA" &&
          "$SYNC" == "Synced" &&
          "$HEALTH" == "Healthy" &&
          "$PHASE" == "Succeeded" ]]; then
        SUCCESS=1
        break
    fi

    if [[ "$PHASE" == "Failed" || "$PHASE" == "Error" ]]; then
        kubectl -n "$ARGO_NS" get application "$APP" -o yaml
        fail "ArgoCD deployment failed."
    fi

    sleep 5
done

[[ "$SUCCESS" == "1" ]] ||
    fail "Timed out waiting for ArgoCD Healthy/Synced/Succeeded."

log "15. KUBERNETES HEALTH"

kubectl get nodes -o wide

echo
echo "Problematic pods:"
kubectl get pods -A \
    --field-selector=status.phase!=Running,status.phase!=Succeeded \
    2>/dev/null || true

echo
echo "Deployments:"
kubectl get deployments -A

log "16. FINAL GIT STATE"

git fetch "$REMOTE" "$BRANCH"

FINAL_LOCAL="$(git rev-parse HEAD)"
FINAL_REMOTE="$(git rev-parse "$REMOTE/$BRANCH")"

echo "Local : $FINAL_LOCAL"
echo "Remote: $FINAL_REMOTE"

[[ "$FINAL_LOCAL" == "$NEW_SHA" ]] ||
    fail "Local HEAD changed unexpectedly."

[[ "$FINAL_REMOTE" == "$NEW_SHA" ]] ||
    fail "GitHub main changed unexpectedly."

echo
echo "Remaining working-tree changes:"
git status --short

log "17. FINAL ARGOCD STATE"

kubectl -n "$ARGO_NS" get application "$APP" \
    -o jsonpath='SYNC={.status.sync.status} HEALTH={.status.health.status} PHASE={.status.operationState.phase} REV={.status.sync.revision}{"\n"}'

log "18. PUBLIC HEALTH CHECKS"

HEALTH_URLS=(
    "https://api.shopnoltd.dpdns.org/healthz"
    "https://api.shopnoltd.dpdns.org/readyz"
    "https://remote.shopnoltd.dpdns.org/healthz"
)

for URL in "${HEALTH_URLS[@]}"; do
    echo
    echo "CHECK: $URL"

    curl --fail --silent --show-error \
        --connect-timeout 10 \
        --max-time 20 \
        "$URL" ||
        fail "Health check failed: $URL"

    echo
done

log "SHOPNOLTD SAFE UPDATE COMPLETE"

echo "Commit : $NEW_SHA"
echo "Branch : $BRANCH"
echo "ArgoCD : Synced / Healthy / Succeeded"
echo
echo "GitOps deployment completed successfully."
echo "No kubectl apply was used."
echo "No pods were manually deleted."
echo "Only explicitly supplied files were staged."
echo "Pre-existing unrelated changes were protected."
