#!/usr/bin/env bash
# Backend smoke test for shopnoltd.dpdns.org
# 1. Run discover_endpoints.sh FIRST and fill in the hostnames below.
# 2. This tries 3 login strategies in order and uses whichever works.
# 3. Rotate both test passwords after this session — they were pasted in chat.
set -uo pipefail  # no -e: we want to keep going after failed checks and report everything

# ── FILL IN FROM discover_endpoints.sh OUTPUT ───────────────────────────────
BASE="shopnoltd.dpdns.org"
GATEWAY_HOST="gateway.${BASE}"            # TODO confirm
AUTH_HOST="auth-service.${BASE}"          # TODO confirm
KEYCLOAK_HOST="keycloak.${BASE}"          # TODO confirm — hostname may differ
WEB_PORTAL_HOST="web-portal.${BASE}"      # TODO confirm
ADMIN_PORTAL_HOST="admin-portal.${BASE}"  # TODO confirm
BILLING_HOST="billing.${BASE}"            # TODO confirm — billing-engine's ingress host
PAYMENT_HOST="payment.${BASE}"            # TODO confirm
EXCHANGE_HOST="exchange.${BASE}"          # TODO confirm
BLOG_HOST="blog.${BASE}"                  # TODO confirm — dedicated blog/CMS service host

ADMIN_USER="test_admin"
ADMIN_PASS='GZ5cGMEJ1k8iqaWNdwjiWA'
USER_USER="test_user"
USER_PASS='gnNdipU4lfpLhdS0dUv7IA'

# ── helpers ──────────────────────────────────────────────────────────────
pass=0; fail=0
check() {
  local desc="$1" expect="$2" actual="$3"
  if [[ "$actual" == "$expect" ]]; then
    echo "  OK   $desc (got $actual)"
    pass=$((pass+1))
  else
    echo "  FAIL $desc (expected $expect, got $actual)"
    fail=$((fail+1))
  fi
}

status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

# ── login: try 3 strategies, keep whichever returns a token ────────────────
login() {
  local user="$1" pw="$2" out_token_var="$3"
  local token=""

  # Strategy A: gateway login endpoint
  resp=$(curl -s -X POST "https://${GATEWAY_HOST}/api/v1/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${user}\",\"password\":\"${pw}\"}" 2>/dev/null || true)
  token=$(echo "$resp" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin); print(d.get("access_token") or d.get("token") or "")
except Exception: print("")' 2>/dev/null)
  if [[ -n "$token" ]]; then
    echo "  login via gateway ($GATEWAY_HOST) succeeded for $user"
    printf -v "$out_token_var" '%s' "$token"; return 0
  fi

  # Strategy B: auth-service direct login endpoint
  resp=$(curl -s -X POST "https://${AUTH_HOST}/api/v1/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"${user}\",\"password\":\"${pw}\"}" 2>/dev/null || true)
  token=$(echo "$resp" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin); print(d.get("access_token") or d.get("token") or "")
except Exception: print("")' 2>/dev/null)
  if [[ -n "$token" ]]; then
    echo "  login via auth-service ($AUTH_HOST) succeeded for $user"
    printf -v "$out_token_var" '%s' "$token"; return 0
  fi

  # Strategy C: Keycloak direct grant (only works if Direct Access Grants is enabled)
  resp=$(curl -s -X POST "https://${KEYCLOAK_HOST}/realms/shopnoltd/protocol/openid-connect/token" \
    -d "grant_type=password&client_id=shopnoltd-web&username=${user}&password=${pw}" 2>/dev/null || true)
  token=$(echo "$resp" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin); print(d.get("access_token",""))
except Exception: print("")' 2>/dev/null)
  if [[ -n "$token" ]]; then
    echo "  login via Keycloak direct grant ($KEYCLOAK_HOST) succeeded for $user"
    printf -v "$out_token_var" '%s' "$token"; return 0
  fi

  echo "  All 3 login strategies FAILED for $user — see raw responses above / adjust endpoint paths"
  return 1
}

echo "===== Logging in as admin and non-admin ====="
ADMIN_TOKEN=""; USER_TOKEN=""
login "$ADMIN_USER" "$ADMIN_PASS" ADMIN_TOKEN
login "$USER_USER" "$USER_PASS" USER_TOKEN

AUTHA=(-H "Authorization: Bearer ${ADMIN_TOKEN}")
AUTHU=(-H "Authorization: Bearer ${USER_TOKEN}")

echo
echo "===== Frontend shells reachable (expect 200) ====="
check "web-portal loads"   "200" "$(status https://${WEB_PORTAL_HOST}/)"
check "admin-portal loads" "200" "$(status https://${ADMIN_PORTAL_HOST}/)"
check "blog loads"         "200" "$(status https://${BLOG_HOST}/)"

echo
echo "===== Blog service ====="
# TODO adjust path once you check devtools Network tab on the real blog page
check "blog list API"   "200" "$(status "${AUTHU[@]}" https://${BLOG_HOST}/api/v1/posts)"

echo
echo "===== Admin dashboard (admin token should pass, user token should be denied) ====="
check "admin API - as admin" "200" "$(status "${AUTHA[@]}" https://${ADMIN_PORTAL_HOST}/api/v1/admin/dashboard)"
check "admin API - as user (expect 403)" "403" "$(status "${AUTHU[@]}" https://${ADMIN_PORTAL_HOST}/api/v1/admin/dashboard)"

echo
echo "===== User dashboard ====="
check "user dashboard - as user"  "200" "$(status "${AUTHU[@]}" https://${WEB_PORTAL_HOST}/api/v1/dashboard)"
check "user dashboard - as admin" "200" "$(status "${AUTHA[@]}" https://${WEB_PORTAL_HOST}/api/v1/dashboard)"

echo
echo "===== Billing / Payment / Exchange ====="
check "billing-engine reachable"  "200" "$(status "${AUTHU[@]}" https://${BILLING_HOST}/api/v1/billing/invoices)"
check "payment-service reachable" "200" "$(status "${AUTHU[@]}" https://${PAYMENT_HOST}/api/v1/payments/methods)"
check "exchange-service reachable" "200" "$(status "${AUTHU[@]}" https://${EXCHANGE_HOST}/api/v1/exchange/rates)"

echo
echo "============================================================"
echo "RESULT: $pass passed, $fail failed"
echo "============================================================"
