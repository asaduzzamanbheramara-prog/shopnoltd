#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
FAILED=()

for d in k8s/services/*/; do
  [ -d "$d" ] || continue
  svc=$(basename "$d")
  if kubectl apply -k "$d" --dry-run=client >/dev/null 2>&1; then
    echo "✅ $svc"
    ((PASS++))
  else
    err=$(kubectl apply -k "$d" --dry-run=client 2>&1 | tail -1)
    echo "❌ $svc  →  $err"
    ((FAIL++))
    FAILED+=("$svc")
  fi
done

echo
echo "============================="
echo "  PASS: $PASS   FAIL: $FAIL"
echo "============================="
[ ${#FAILED[@]} -gt 0 ] && printf 'Failed: %s\n' "${FAILED[@]}"
