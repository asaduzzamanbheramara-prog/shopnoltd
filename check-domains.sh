#!/usr/bin/env bash
# Shopnoltd — full domain/subdomain functionality audit
# Run from WSL2: bash check-domains.sh

INGRESS_IP="172.30.206.152"   # ingress-nginx-controller external IP
TIMEOUT=6

# All hosts currently in the ingress table (primary host per rule; add extra
# hosts on the same line separated by space if a rule has multiple)
declare -A HOSTS=(
  [chatwoot]="chatwoot.shopnoltd.dpdns.org"
  [code-server]="code-server.shopnoltd.dpdns.org"
  [enketo]="enketo.shopnoltd.dpdns.org"
  [gitea]="gitea.shopnoltd.dpdns.org"
  [kobotoolbox]="kobotoolbox.shopnoltd.dpdns.org kobo.shopnoltd.dpdns.org"
  [n8n]="n8n.shopnoltd.dpdns.org"
  [onlyoffice]="onlyoffice.shopnoltd.dpdns.org"
  [owncast]="owncast.shopnoltd.dpdns.org"
  [minio]="minio.shopnoltd.dpdns.org"
  [postgres]="postgres.shopnoltd.dpdns.org"
  [redis]="redis.shopnoltd.dpdns.org"
  [auth-service]="auth-service.shopnoltd.dpdns.org"
  [keycloak]="auth.shopnoltd.dpdns.org keycloak.shopnoltd.dpdns.org"
  [oauth-service]="oauth-service.shopnoltd.dpdns.org"
  [mail-service]="api.mail.shopnoltd.dpdns.org"
  [alertmanager]="alertmanager.shopnoltd.dpdns.org"
  [loki]="loki.shopnoltd.dpdns.org"
  [billing-engine]="billing.shopnoltd.dpdns.org"
  [admin-portal]="admin-portal.shopnoltd.dpdns.org"
  [ai-platform]="ai-platform.shopnoltd.dpdns.org"
  [analytics-service]="analytics-service.shopnoltd.dpdns.org"
  [android-portal]="shopnoltdandroid.shopnoltd.dpdns.org"
  [api-service]="api.shopnoltd.dpdns.org"
  [audit-service]="audit-service.shopnoltd.dpdns.org"
  [domain-service]="domain.shopnoltd.dpdns.org"
  [event-service]="event.shopnoltd.dpdns.org"
  [foundation-service]="foundation.shopnoltd.dpdns.org"
  [freedomain-service]="freedomain.shopnoltd.dpdns.org"
  [gateway]="gateway.shopnoltd.dpdns.org"
  [interior-service]="interior.shopnoltd.dpdns.org"
  [license-service]="license-service.shopnoltd.dpdns.org"
  [mobile-api]="mobile-api.shopnoltd.dpdns.org"
  [notification-service]="notification-service.shopnoltd.dpdns.org"
  [report-service]="report-service.shopnoltd.dpdns.org"
  [storage-service]="storage-service.shopnoltd.dpdns.org"
  [tenant-router]="tenant-router.shopnoltd.dpdns.org"
  [training-service]="training.shopnoltd.dpdns.org"
  [web-portal]="web-portal.shopnoltd.dpdns.org"
  [worker-service]="worker-service.shopnoltd.dpdns.org"
  [toolbox-kf]="kf.shopnoltd.dpdns.org"
)

RESULTS_FILE=$(mktemp)

check_one() {
  local svc="$1" host="$2"

  # Direct to ingress-nginx (bypasses DNS/Cloudflare, HTTPS with SNI, ignore cert)
  local direct_code direct_time
  read -r direct_code direct_time < <(curl -sk -o /dev/null \
    --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" \
    -w "%{http_code} %{time_total}" \
    --resolve "${host}:443:${INGRESS_IP}" \
    "https://${host}/" 2>/dev/null)
  direct_code="${direct_code:-000}"
  direct_time="${direct_time:-0}"

  # Full external path via public DNS + Cloudflare tunnel
  local ext_code
  ext_code=$(curl -sk -o /dev/null \
    --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" \
    -w "%{http_code}" \
    "https://${host}/" 2>/dev/null)
  ext_code="${ext_code:-000}"

  echo "${svc}|${host}|${direct_code}|${ext_code}|${direct_time}" >> "$RESULTS_FILE"
}

echo "============================================================"
echo "SHOPNOLTD — DOMAIN/SUBDOMAIN FUNCTIONALITY AUDIT"
echo "Testing $(echo "${!HOSTS[@]}" | wc -w) services, $(for h in "${HOSTS[@]}"; do echo "$h"; done | wc -w) hostnames"
echo "============================================================"
echo

for svc in "${!HOSTS[@]}"; do
  for host in ${HOSTS[$svc]}; do
    check_one "$svc" "$host" &
  done
  # throttle: don't fork 90 curls at once
  while [ "$(jobs -r | wc -l)" -ge 15 ]; do wait -n; done
done
wait

# --- Report ---
printf "%-22s %-42s %-8s %-8s %-8s\n" "SERVICE" "HOST" "DIRECT" "EXTERN" "TIME(s)"
printf '%.0s-' {1..92}; echo

FAIL_COUNT=0
sort -t'|' -k1,1 "$RESULTS_FILE" | while IFS='|' read -r svc host direct_code ext_code direct_time; do
  status="OK"
  if [[ "$direct_code" -lt 200 || "$direct_code" -ge 400 || "$direct_code" == "000" ]]; then
    status="FAIL"
  fi
  printf "%-22s %-42s %-8s %-8s %-8s  [%s]\n" "$svc" "$host" "$direct_code" "$ext_code" "$direct_time" "$status"
done

echo
echo "============================================================"
echo "Legend: DIRECT = curl straight to ingress-nginx (bypasses DNS/CF tunnel)"
echo "        EXTERN = curl via public DNS + Cloudflare tunnel"
echo "        000    = connection failed/timed out"
echo "A DIRECT failure means the ingress route or backend pod is broken."
echo "A DIRECT pass + EXTERN failure points at DNS or the Cloudflare tunnel."
echo "============================================================"

rm -f "$RESULTS_FILE"
