#!/usr/bin/env bash
set -euo pipefail

# Idempotently ensure public service hostnames point at the existing Cloudflare Tunnel.
# The API token is supplied at runtime only; it is never stored in Git or printed.
# Preferred source is the existing Kubernetes Secret on the trusted self-hosted runner.
# A GitHub Actions secret/runtime environment variable may be used as a safe fallback.

ZONE_NAME="${CLOUDFLARE_ZONE_NAME:-shopnoltd.dpdns.org}"
SECRET_NAMESPACE="${CLOUDFLARE_SECRET_NAMESPACE:-shopno-ingress}"
SECRET_NAME="${CLOUDFLARE_SECRET_NAME:-cloudflare-api-token}"
TUNNEL_TARGET="${CLOUDFLARE_TUNNEL_TARGET:-5d6e037a-7c09-4788-8532-11dba5fc1a72.cfargotunnel.com}"

command -v kubectl >/dev/null || { echo "ERROR: kubectl is required" >&2; exit 1; }
command -v curl >/dev/null || { echo "ERROR: curl is required" >&2; exit 1; }
command -v jq >/dev/null || { echo "ERROR: jq is required" >&2; exit 1; }

CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"
secret_json=""

if [ -z "$CLOUDFLARE_API_TOKEN" ] && kubectl -n "$SECRET_NAMESPACE" get secret "$SECRET_NAME" >/dev/null 2>&1; then
  secret_json="$(kubectl -n "$SECRET_NAMESPACE" get secret "$SECRET_NAME" -o json)"
  mapfile -t keys < <(jq -r '.data | keys[]' <<<"$secret_json")
  if [ "${#keys[@]}" -ne 1 ]; then
    echo "ERROR: expected exactly one data key in ${SECRET_NAMESPACE}/${SECRET_NAME}; found ${#keys[@]}." >&2
    exit 1
  fi
  secret_key="${keys[0]}"
  CLOUDFLARE_API_TOKEN="$(jq -r --arg k "$secret_key" '.data[$k]' <<<"$secret_json" | base64 -d)"
fi

export CLOUDFLARE_API_TOKEN
trap 'unset CLOUDFLARE_API_TOKEN secret_json' EXIT

if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
  echo "ERROR: Cloudflare DNS API token is unavailable." >&2
  echo "Provide the existing ${SECRET_NAMESPACE}/${SECRET_NAME} Secret or the runtime CLOUDFLARE_API_TOKEN credential." >&2
  exit 1
fi

api="https://api.cloudflare.com/client/v4"
headers=( -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" -H 'Content-Type: application/json' )

zone_response="$(curl -fsS "${headers[@]}" "$api/zones?name=${ZONE_NAME}&status=active&per_page=1")"
zone_id="$(jq -r '.result[0].id // empty' <<<"$zone_response")"
if [ -z "$zone_id" ]; then
  echo "ERROR: active Cloudflare zone ${ZONE_NAME} was not found." >&2
  exit 1
fi

ensure_cname() {
  local hostname="$1"
  local record_response record_id payload upsert_response

  record_response="$(curl -fsS "${headers[@]}" \
    --get "$api/zones/$zone_id/dns_records" \
    --data-urlencode "type=CNAME" \
    --data-urlencode "name=$hostname" \
    --data-urlencode 'per_page=1')"
  record_id="$(jq -r '.result[0].id // empty' <<<"$record_response")"

  payload="$(jq -cn \
    --arg name "$hostname" \
    --arg content "$TUNNEL_TARGET" \
    '{type:"CNAME",name:$name,content:$content,ttl:1,proxied:true,comment:"Shopnoltd Cloudflare Tunnel managed by GitOps"}')"

  if [ -n "$record_id" ]; then
    upsert_response="$(curl -fsS "${headers[@]}" -X PUT "$api/zones/$zone_id/dns_records/$record_id" --data "$payload")"
  else
    upsert_response="$(curl -fsS "${headers[@]}" -X POST "$api/zones/$zone_id/dns_records" --data "$payload")"
  fi

  if [ "$(jq -r '.success' <<<"$upsert_response")" != "true" ]; then
    echo "ERROR: Cloudflare rejected DNS reconciliation for $hostname." >&2
    jq -c '.errors' <<<"$upsert_response" >&2
    exit 1
  fi
  echo "DNS reconciled: $hostname -> $TUNNEL_TARGET"
}

ensure_cname "social.${ZONE_NAME}"
ensure_cname "social-service.${ZONE_NAME}"
ensure_cname "chat.${ZONE_NAME}"
ensure_cname "chatwoot.${ZONE_NAME}"
ensure_cname "android.${ZONE_NAME}"
