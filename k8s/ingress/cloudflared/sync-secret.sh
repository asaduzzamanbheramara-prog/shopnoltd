#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${CLOUDFLARED_ENV_FILE:-${SCRIPT_DIR}/secret.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: Cloudflare credential env file not found: $ENV_FILE" >&2
  echo "Create it from secret.env.example and keep it outside Git." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${CREDENTIALS_JSON:?CREDENTIALS_JSON is required in $ENV_FILE}"

if [[ "$CREDENTIALS_JSON" == *REPLACE_WITH_REAL* ]]; then
  echo "ERROR: CREDENTIALS_JSON is still a placeholder." >&2
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is required." >&2
  exit 1
fi

kubectl -n shopno-ingress create secret generic cloudflared-creds \
  --from-literal=credentials.json="$CREDENTIALS_JSON" \
  --dry-run=client -o yaml | kubectl apply -f -

unset CREDENTIALS_JSON

echo "Cloudflared credential Secret synchronized without printing the credential."
kubectl -n shopno-ingress rollout restart deployment/cloudflared
kubectl -n shopno-ingress rollout status deployment/cloudflared --timeout=180s
