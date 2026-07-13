#!/usr/bin/env bash
# Deploy every service in dependency-reasonable order, with the same
# auto-rollback/diagnosis safety net as deploy-service.sh, and print a
# pass/fail summary at the end.
#
# Usage: ./scripts/deploy-all.sh [--auto-rollback]
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARGS=("$@")

# Rough dependency order per docs/SERVICE_TOPOLOGY.md: shared infra first,
# identity next, then everything else, business verticals last.
ORDER=(postgres redis minio keycloak oauth-service auth-service gateway tenant-router)
ALL_SERVICES=($(ls k8s/services))
REST=()
for s in "${ALL_SERVICES[@]}"; do
  skip=0
  for o in "${ORDER[@]}"; do [ "$s" == "$o" ] && skip=1; done
  [ "$skip" -eq 0 ] && REST+=("$s")
done

PASSED=()
FAILED=()

for svc in "${ORDER[@]}" "${REST[@]}"; do
  [ -d "k8s/services/$svc" ] || continue
  echo
  echo "======================================================================"
  echo " $svc"
  echo "======================================================================"
  if ./scripts/deploy-service.sh "$svc" "${ARGS[@]}"; then
    PASSED+=("$svc")
  else
    FAILED+=("$svc")
  fi
done

echo
echo "======================= SUMMARY ======================="
echo "Passed (${#PASSED[@]}): ${PASSED[*]:-none}"
echo "Failed (${#FAILED[@]}): ${FAILED[*]:-none}"
[ "${#FAILED[@]}" -eq 0 ]
