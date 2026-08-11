#!/usr/bin/env bash
# Shopnoltd — kobotoolbox functional smoke test
# Covers: signup -> login -> mail-trigger -> redirect -> authenticated endpoint checks
# Run from WSL2: bash kobotoolbox-functional-check.sh

set -uo pipefail

BASE="https://kobo.shopnoltd.dpdns.org"
JAR="/tmp/kobo-functional-cookies.txt"
TS=$(date +%s%N)
USERNAME="functest${TS}"
EMAIL="functest${TS}@example.com"
PASSWORD="FuncTest123!"
RESULTS=()

pass() { RESULTS+=("[PASS] $1"); echo "[PASS] $1"; }
fail() { RESULTS+=("[FAIL] $1 -- $2"); echo "[FAIL] $1 -- $2"; }

rm -f "$JAR"

echo "== 1. Signup page reachable + CSRF token present =="
curl -s -c "$JAR" "$BASE/accounts/signup/" -o /tmp/signup.html -w "HTTP_CODE:%{http_code}\n" > /tmp/signup_code.txt
CODE=$(grep -oP 'HTTP_CODE:\K[0-9]+' /tmp/signup_code.txt)
CSRF=$(grep -oP 'csrfmiddlewaretoken["\s]+value["\s]*=["\s]*\K[^"]+' /tmp/signup.html | head -1)
if [ "$CODE" = "200" ] && [ -n "$CSRF" ]; then
  pass "Signup page loads, CSRF token found"
else
  fail "Signup page" "HTTP $CODE, CSRF present=$([ -n "$CSRF" ] && echo yes || echo no)"
fi

echo "== 2. Create account =="
curl -s -o /tmp/signup_result.html -w "HTTP_CODE:%{http_code}\n" \
  -b "$JAR" -c "$JAR" \
  -X POST "$BASE/accounts/signup/" \
  -H "Referer: $BASE/accounts/signup/" \
  -H "Origin: $BASE" \
  --max-time 30 \
  --data-urlencode "csrfmiddlewaretoken=$CSRF" \
  --data-urlencode "name=Func Test" \
  --data-urlencode "username=$USERNAME" \
  --data-urlencode "email=$EMAIL" \
  --data-urlencode "password1=$PASSWORD" \
  --data-urlencode "password2=$PASSWORD" > /tmp/signup_post_code.txt
SIGNUP_CODE=$(grep -oP 'HTTP_CODE:\K[0-9]+' /tmp/signup_post_code.txt)
if [ "$SIGNUP_CODE" = "200" ] || [ "$SIGNUP_CODE" = "302" ]; then
  pass "Account creation POST (HTTP $SIGNUP_CODE)"
else
  fail "Account creation POST" "HTTP $SIGNUP_CODE -- check /tmp/signup_result.html"
fi
if grep -qiE "error|already exists|invalid" /tmp/signup_result.html; then
  fail "Account creation content check" "Error text found in response -- see /tmp/signup_result.html"
fi

echo "== 3. Login with new account =="
curl -s -c "$JAR" -b "$JAR" "$BASE/accounts/login/" -o /tmp/login.html
LOGIN_CSRF=$(grep -oP 'csrfmiddlewaretoken["\s]+value["\s]*=["\s]*\K[^"]+' /tmp/login.html | head -1)
LOGIN_CODE=$(curl -s -o /tmp/login_result.html -w "%{http_code}" \
  -b "$JAR" -c "$JAR" \
  -X POST "$BASE/accounts/login/" \
  -H "Referer: $BASE/accounts/login/" \
  -H "Origin: $BASE" \
  --max-time 30 \
  --data-urlencode "csrfmiddlewaretoken=$LOGIN_CSRF" \
  --data-urlencode "login=$USERNAME" \
  --data-urlencode "password=$PASSWORD")
if [ "$LOGIN_CODE" = "200" ] || [ "$LOGIN_CODE" = "302" ]; then
  pass "Login POST (HTTP $LOGIN_CODE)"
else
  fail "Login POST" "HTTP $LOGIN_CODE"
fi

echo "== 4. Redirect behavior after login =="
REDIRECT_CHECK=$(curl -s -o /dev/null -w "%{redirect_url}" -b "$JAR" "$BASE/")
if [ -n "$REDIRECT_CHECK" ]; then
  pass "Root redirects to: $REDIRECT_CHECK"
else
  # some apps 200 straight through instead of redirecting -- treat as informational
  echo "[INFO] No redirect_url captured -- root may 200 directly, checking session instead"
fi

echo "== 5. Authenticated session check (dashboard/home reachable, not bounced to login) =="
HOME_CODE=$(curl -s -o /tmp/home.html -w "%{http_code}" -b "$JAR" "$BASE/")
if [ "$HOME_CODE" = "200" ] && ! grep -qi "accounts/login" /tmp/home.html; then
  pass "Authenticated home page loads without login bounce (HTTP $HOME_CODE)"
else
  fail "Authenticated session" "HTTP $HOME_CODE or bounced to login -- see /tmp/home.html"
fi

echo "== 6. Mail dispatch trigger (password reset flow, checks 200/302 not 500) =="
curl -s -c "$JAR" "$BASE/accounts/password/reset/" -o /tmp/pwreset.html
RESET_CSRF=$(grep -oP 'csrfmiddlewaretoken["\s]+value["\s]*=["\s]*\K[^"]+' /tmp/pwreset.html | head -1)
RESET_CODE=$(curl -s -o /tmp/pwreset_result.html -w "%{http_code}" \
  -b "$JAR" -X POST "$BASE/accounts/password/reset/" \
  -H "Referer: $BASE/accounts/password/reset/" \
  --data-urlencode "csrfmiddlewaretoken=$RESET_CSRF" \
  --data-urlencode "email=$EMAIL")
if [ "$RESET_CODE" = "200" ] || [ "$RESET_CODE" = "302" ]; then
  pass "Password reset (mail trigger) submitted (HTTP $RESET_CODE) -- verify actual delivery via mail-service logs"
else
  fail "Password reset (mail trigger)" "HTTP $RESET_CODE"
fi

echo "== 7. Static assets serving correctly (CSS/JS not 404) =="
STATIC_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/static/")
# static index listing may 403/404 depending on config -- check a known JS/CSS bundle instead if this fails
if [ "$STATIC_CODE" != "404" ]; then
  pass "Static root not 404 (HTTP $STATIC_CODE) -- static-map appears active"
else
  fail "Static assets" "HTTP 404 -- static-map may not be applying, check specific bundle path"
fi

echo ""
echo "============================================================"
echo "SUMMARY"
echo "============================================================"
printf '%s\n' "${RESULTS[@]}"
echo "============================================================"
echo "Artifacts saved: /tmp/signup.html /tmp/signup_result.html /tmp/login.html /tmp/login_result.html /tmp/home.html /tmp/pwreset_result.html"
echo "Test account: username=$USERNAME email=$EMAIL"
