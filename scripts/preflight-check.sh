#!/usr/bin/env bash
# Catches the most common "why won't this deploy" cause before you even talk
# to the cluster: a secret.yaml that still has REPLACE_WITH_BASE64 in it.
#
# Usage: ./scripts/preflight-check.sh [service-name]
#   (no argument = check every service)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SERVICES_DIR="k8s/services"
TARGET="${1:-}"
FAILED=0

check_service() {
  local svc="$1"
  local dir="$SERVICES_DIR/$svc"
  [ -d "$dir" ] || { echo "no such service: $svc"; return 1; }

  local problems=0

  if [ -f "$dir/secret.yaml" ] && grep -q "REPLACE_WITH_BASE64" "$dir/secret.yaml"; then
    echo "  [FAIL] $svc: secret.yaml has unfilled placeholders"
    grep -B1 "REPLACE_WITH_BASE64" "$dir/secret.yaml" | grep -v "^--$" | sed 's/^/         /'
    echo "         Fix: docs/SECRETS.md (Option A for quick local, Option B for sealed-secrets)"
    problems=1
  fi

  if [ ! -f "$dir/secret.yaml" ] && grep -q "secret.yaml" "$dir/kustomization.yaml" 2>/dev/null; then
    echo "  [FAIL] $svc: kustomization.yaml references secret.yaml but it doesn't exist"
    echo "         Fix: python3 scripts/generate_missing_secrets.py"
    problems=1
  fi

  if grep -rq "shopnoltd\.com" "$dir" 2>/dev/null; then
    echo "  [FAIL] $svc: still references shopnoltd.com (should be shopnoltd.dpdns.org)"
    problems=1
  fi

  if [ "$problems" -eq 0 ]; then
    echo "  [OK]   $svc"
  else
    FAILED=1
  fi
}

if [ -n "$TARGET" ]; then
  check_service "$TARGET"
else
  for d in "$SERVICES_DIR"/*/; do
    check_service "$(basename "$d")"
  done
fi

if [ "$FAILED" -eq 1 ]; then
  echo
  echo "Preflight found problems above -- fix those before deploying, or"
  echo "deploy-service.sh will just fail at the cluster with a less specific error."
  exit 1
fi
echo
echo "Preflight passed."
