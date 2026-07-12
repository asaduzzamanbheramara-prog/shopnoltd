#!/usr/bin/env bash
echo "===================================================================="
echo "  FINAL FULL DOMAIN CHECK — $(date)"
echo "===================================================================="

check() {
  local desc="$1"
  local url="$2"
  printf "%-50s " "$desc"
  curl -s -o /dev/null -w "HTTP %{http_code}  (%{time_total}s)\n" -L --max-time 15 "$url"
}

echo -e "\n--- Public domains (via Cloudflare Tunnel) ---"
check "Root"              "https://shopnoltd.dpdns.org/"
check "KPI (kc)"          "https://kobo.shopnoltd.dpdns.org/"
check "KPI alt (kc)"      "https://kc.shopnoltd.dpdns.org/"
check "KoboCAT (kf)"      "https://kf.shopnoltd.dpdns.org/accounts/login/?next=/kobocat/"
check "Enketo"            "https://enketo.shopnoltd.dpdns.org/"
check "Chat"              "https://chat.shopnoltd.dpdns.org/"
check "Live"              "https://live.shopnoltd.dpdns.org/"
check "Meet"              "https://meet.shopnoltd.dpdns.org/"
check "Grafana"           "https://grafana.shopnoltd.dpdns.org/"
check "Prometheus"        "https://prometheus.shopnoltd.dpdns.org/"
check "Freedomain"        "https://freedomain.shopnoltd.dpdns.org/"

echo -e "\n===================================================================="
echo "  DONE"
echo "===================================================================="
