#!/usr/bin/env bash
set -euo pipefail

# Capacity guard for the live PostgreSQL PVC. This does not resize or recreate
# the PVC; it fails early when the database filesystem is getting too full.

POSTGRES_NAMESPACE="${POSTGRES_NAMESPACE:-shopno-data}"
POSTGRES_DEPLOYMENT="${POSTGRES_DEPLOYMENT:-postgres}"
MAX_USED_PERCENT="${MAX_USED_PERCENT:-80}"

pod="$(kubectl -n "$POSTGRES_NAMESPACE" get pods \
  -l app.kubernetes.io/name=postgres \
  -o jsonpath='{.items[0].metadata.name}')"

if [[ -z "$pod" ]]; then
  echo "PostgreSQL pod not found" >&2
  exit 1
fi

capacity="$(kubectl -n "$POSTGRES_NAMESPACE" get pvc postgres-data \
  -o jsonpath='{.status.capacity.storage}')"

usage_line="$(kubectl -n "$POSTGRES_NAMESPACE" exec "$pod" -- \
  sh -c 'df -P /var/lib/postgresql/data | tail -n 1')"

used_percent="$(awk '{gsub(/%/,"",$5); print $5}' <<<"$usage_line")"

[[ "$used_percent" =~ ^[0-9]+$ ]] || {
  echo "Unable to parse PostgreSQL filesystem usage: $usage_line" >&2
  exit 1
}

printf 'PostgreSQL PVC capacity: %s\n' "${capacity:-unknown}"
printf 'PostgreSQL filesystem usage: %s%%\n' "$used_percent"
printf 'Configured maximum usage: %s%%\n' "$MAX_USED_PERCENT"

if (( used_percent >= MAX_USED_PERCENT )); then
  echo "PostgreSQL storage is above the safety threshold; expand capacity before it reaches exhaustion." >&2
  exit 2
fi
