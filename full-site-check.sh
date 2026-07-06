#!/usr/bin/env bash
echo "===================================================================="
echo "  FULL SITE / PAGE LIVE CHECK — $(date)"
echo "===================================================================="

check() {
  local desc="$1"
  local host="$2"
  local path="$3"
  printf "%-55s " "$desc"
  code=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $host" --max-time 10 "http://localhost${path}")
  time=$(curl -s -o /dev/null -w "%{time_total}" -H "Host: $host" --max-time 10 "http://localhost${path}")
  if [[ "$code" =~ ^(200|301|302|304)$ ]]; then
    echo "OK   HTTP $code  (${time}s)"
  else
    echo "FAIL HTTP $code  (${time}s)"
  fi
}

echo -e "\n--- Root / Marketing / Frontend Sites ---"
check "Root app (shopnoltd.dpdns.org)"           "shopnoltd.dpdns.org"          "/"
check "Freedomain UI"                             "freedomain.shopnoltd.dpdns.org" "/"

echo -e "\n--- App/API Services (real endpoints) ---"
check "API service /health"                       "api.shopnoltd.dpdns.org"      "/health"
check "Auth/OAuth service /"                      "auth.shopnoltd.dpdns.org"     "/"
check "Billing engine /health"                    "billing.shopnoltd.dpdns.org"  "/health"

echo -e "\n--- Chat / Live / Meet ---"
check "Chat"                                      "chat.shopnoltd.dpdns.org"     "/"
check "Live (Owncast)"                            "live.shopnoltd.dpdns.org"     "/"
check "Meet (Jitsi)"                              "meet.shopnoltd.dpdns.org"     "/"

echo -e "\n--- Monitoring ---"
check "Grafana"                                   "grafana.shopnoltd.dpdns.org"  "/"
check "Prometheus"                                "prometheus.shopnoltd.dpdns.org" "/"

echo -e "\n--- KoboToolbox Stack ---"
check "KPI (kc) root"                             "kobo.shopnoltd.dpdns.org"     "/"
check "KoboCAT (kf)"                              "kf.shopnoltd.dpdns.org"       "/"
check "kobo.local /kc"                            "kobo.local"                  "/kc"
check "kobo.local /kf"                            "kobo.local"                  "/kf"
check "kobo.local /ee (Enketo)"                   "kobo.local"                  "/ee"

echo -e "\n--- Wildcard / Tenant Router ---"
check "Wildcard subdomain (test.shopnoltd.dpdns.org)" "test.shopnoltd.dpdns.org" "/"

echo -e "\n===================================================================="
echo "  SITE CHECK COMPLETE"
echo "===================================================================="
