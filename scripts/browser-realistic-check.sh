#!/usr/bin/env bash
# check-branding-full.sh
# Combines the Host-header / --resolve approach from browser-realistic-check.sh
# with branding-leak detection (kobo strings + old/new asset paths).
# Tests against 127.0.0.1:80 directly, so it works even before/without the
# Cloudflare tunnel, and lets you catch mislabeled routing (kf vs kc vs kobo.local).

set -uo pipefail

REPORT="branding-full-report-$(date +%Y%m%d-%H%M).txt"
echo "==================================================================" | tee "$REPORT"
echo "  FULL BRANDING + ROUTING CHECK — $(date)" | tee -a "$REPORT"
echo "==================================================================" | tee -a "$REPORT"

check_full() {
  local desc="$1" host="$2" path="$3"
  echo "" | tee -a "$REPORT"
  echo "== $desc  (Host: $host  Path: $path) ==" | tee -a "$REPORT"

  curl -s -L -H "Host: $host" --max-time 15 \
    -w "  Redirect hops: %{num_redirects}  Final status: %{http_code}  Content-Type: %{content_type}  Size: %{size_download}b\n" \
    -o /tmp/check_body.html \
    "http://localhost${path}" \
    --resolve "${host}:80:127.0.0.1" 2>&1 | tee -a "$REPORT"

  if grep -qi "<html" /tmp/check_body.html 2>/dev/null; then
    title=$(grep -oPi '(?<=<title>).*?(?=</title>)' /tmp/check_body.html | head -1)
    echo "  Title: ${title:-<none found>}" | tee -a "$REPORT"
  else
    echo "  WARNING: response doesn't look like HTML" | tee -a "$REPORT"
  fi

  # Branding leak check
  local hits
  hits=$(grep -io 'kobo[a-z]*' /tmp/check_body.html 2>/dev/null | sort -u | tr '\n' ' ')
  if [[ -n "$hits" ]]; then
    echo "  [LEAK] kobo strings found: $hits" | tee -a "$REPORT"
  else
    echo "  [OK] no kobo strings in body" | tee -a "$REPORT"
  fi

  # Asset path probes (only meaningful for kf/kc/ee-style hosts, harmless elsewhere)
  for asset in \
    "static/images/kobologo.svg" \
    "static/images/shopnoltdlogo.svg" \
    "static/css/kobo-branding.css" \
    "static/css/shopnoltd-branding.css"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
      -H "Host: $host" --resolve "${host}:80:127.0.0.1" \
      "http://localhost${path%/}/${asset}")
    echo "    ${path}/${asset} -> ${code}" | tee -a "$REPORT"
  done
}

echo -e "\n############ ROOT / MARKETING ############" | tee -a "$REPORT"
check_full "Root site"        "shopnoltd.dpdns.org"           "/"
check_full "Freedomain UI"    "freedomain.shopnoltd.dpdns.org" "/"
check_full "Domain manager"   "domain.shopnoltd.dpdns.org"     "/"

echo -e "\n############ APPS ############" | tee -a "$REPORT"
check_full "Chat"             "chat.shopnoltd.dpdns.org"  "/"
check_full "Live (Owncast)"   "live.shopnoltd.dpdns.org"  "/"
check_full "Meet (Jitsi)"     "meet.shopnoltd.dpdns.org"  "/"
check_full "Event"            "event.shopnoltd.dpdns.org" "/"
check_full "Interior"         "interior.shopnoltd.dpdns.org" "/"
check_full "Foundation"       "foundation.shopnoltd.dpdns.org" "/"

echo -e "\n############ CORE API / AUTH / BILLING ############" | tee -a "$REPORT"
check_full "API"              "api.shopnoltd.dpdns.org"     "/"
check_full "Auth"             "auth.shopnoltd.dpdns.org"    "/"
check_full "Billing"          "billing.shopnoltd.dpdns.org" "/"
check_full "Mail"             "mail.shopnoltd.dpdns.org"    "/"

echo -e "\n############ KOBOTOOLBOX STACK (subdomain routing) ############" | tee -a "$REPORT"
check_full "kobo subdomain"   "kobo.shopnoltd.dpdns.org" "/"
check_full "kf subdomain"     "kf.shopnoltd.dpdns.org"   "/"
check_full "kc subdomain"     "kc.shopnoltd.dpdns.org"   "/"
check_full "ee subdomain"     "ee.shopnoltd.dpdns.org"   "/"
check_full "enketo subdomain" "enketo.shopnoltd.dpdns.org" "/"

echo -e "\n############ KOBOTOOLBOX STACK (path-based routing on kobo.local) ############" | tee -a "$REPORT"
check_full "kobo.local /kc"   "kobo.local" "/kc"
check_full "kobo.local /kf"   "kobo.local" "/kf"
check_full "kobo.local /ee"   "kobo.local" "/ee"

echo -e "\n############ MONITORING / ADMIN (internal — branding not expected) ############" | tee -a "$REPORT"
check_full "Grafana"          "grafana.shopnoltd.dpdns.org"    "/"
check_full "Prometheus"       "prometheus.shopnoltd.dpdns.org" "/"
check_full "pgAdmin"          "pgadmin.shopnoltd.dpdns.org"    "/"
check_full "Portainer"        "portainer.shopnoltd.dpdns.org"  "/"

echo -e "\n############ WILDCARD / TENANT ROUTING ############" | tee -a "$REPORT"
check_full "Tenant (test)"    "test.shopnoltd.dpdns.org" "/"
check_full "Tenant (demo)"    "demo.shopnoltd.dpdns.org" "/"

rm -f /tmp/check_body.html

echo "" | tee -a "$REPORT"
echo "==================================================================" | tee -a "$REPORT"
echo "  CHECK COMPLETE. Report saved to: $REPORT" | tee -a "$REPORT"
echo "==================================================================" | tee -a "$REPORT"
