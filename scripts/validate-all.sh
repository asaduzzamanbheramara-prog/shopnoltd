#!/usr/bin/env bash
# Validates every k8s/services/* manifest.
set -uo pipefail

PASS=0
FAIL=0
FAILED_SVCS=()

for d in k8s/services/*/; do
  svc=$(basename "$d")
  out=$(kubectl kustomize "$d" 2>&1 >/dev/null) && \
    out=$(kubectl apply -k "$d" --dry-run=server 2>&1 >/dev/null) && \
    out=$(kubectl apply -k "$d" --dry-run=client 2>&1 >/dev/null) || true

  if kubectl apply -k "$d" --dry-run=client >/dev/null 2>&1; then
    echo "✅ $svc"
    ((PASS++))
  else
    err=$(kubectl apply -k "$d" --dry-run=client 2>&1 | tail -1)
    echo "❌ $svc  →  $err"
    ((FAIL++))
    FAILED_SVCS+=("$svc")
  fi
done

echo
echo "============================="
echo "  PASS: $PASS   FAIL: $FAIL"
echo "============================="
[ ${#FAILED_SVCS[@]} -gt 0 ] && printf 'Failed: %s\n' "${FAILED_SVCS[@]}"
