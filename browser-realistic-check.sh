#!/usr/bin/env bash
echo "===================================================================="
echo "  BROWSER-REALISTIC DOMAIN CHECK — $(date)"
echo "===================================================================="

check_full() {
  local desc="$1"
  local host="$2"
  local path="$3"
  echo ""
  echo "== $desc ($host$path) =="
  curl -s -L -H "Host: $host" --max-time 15 \
    -w "\n  Redirect chain: %{num_redirects} hop(s)\n  Final URL:      %{url_effective}\n  Final status:   %{http_code}\n  Content-Type:   %{content_type}\n  Total time:     %{time_total}s\n  Size:           %{size_download} bytes\n" \
    -o /tmp/check_body.html \
    "http://localhost${path}" \
    --resolve "${host}:80:127.0.0.1" 2>&1

  # Show first meaningful content line as a sanity check
  if grep -qi "<html" /tmp/check_body.html 2>/dev/null; then
    title=$(grep -oPi '(?<=<title>).*?(?=</title>)' /tmp/check_body.html | head -1)
    echo "  Page title:     ${title:-<no title tag found>}"
  else
    echo "  WARNING: response body doesn't look like HTML"
    head -c 200 /tmp/check_body.html
    echo ""
  fi
}

echo -e "\n############ ROOT / MARKETING ############"
check_full "Root site"            "shopnoltd.dpdns.org"            "/"
check_full "Freedomain UI"        "freedomain.shopnoltd.dpdns.org"  "/"

echo -e "\n############ APPS ############"
check_full "Chat"                 "chat.shopnoltd.dpdns.org"        "/"
check_full "Live (Owncast)"       "live.shopnoltd.dpdns.org"        "/"
check_full "Meet (Jitsi)"         "meet.shopnoltd.dpdns.org"        "/"

echo -e "\n############ AUTH / MONITORING (redirect-heavy) ############"
check_full "Grafana"              "grafana.shopnoltd.dpdns.org"     "/"
check_full "Prometheus"           "prometheus.shopnoltd.dpdns.org"  "/"

echo -e "\n############ KOBOTOOLBOX STACK ############"
check_full "KPI (kc)"             "kobo.shopnoltd.dpdns.org"        "/"
check_full "KoboCAT (kf)"         "kf.shopnoltd.dpdns.org"          "/"
check_full "kobo.local /kc"       "kobo.local"                      "/kc"
check_full "kobo.local /kf"       "kobo.local"                      "/kf"
check_full "kobo.local /ee"       "kobo.local"                      "/ee"

echo -e "\n############ WILDCARD / TENANT ROUTING ############"
check_full "Tenant subdomain (test)" "test.shopnoltd.dpdns.org"     "/"
check_full "Tenant subdomain (demo)" "demo.shopnoltd.dpdns.org"     "/"

rm -f /tmp/check_body.html

echo -e "\n===================================================================="
echo "  CHECK COMPLETE"
echo "===================================================================="
