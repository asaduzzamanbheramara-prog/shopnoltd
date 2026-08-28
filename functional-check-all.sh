#!/usr/bin/env bash
# shopnoltd — full functional sweep across all services
# Run from shopnoltd-pc-1 (needs kubectl context + network access to the domains)

set -uo pipefail

# ---- Edit these hostnames to match your actual DNS records ----
declare -A SITES=(
  [kobo]="https://kobo.shopnoltd.dpdns.org/"
  [kf]="https://kf.shopnoltd.dpdns.org/"
  [gitea]="https://gitea.shopnoltd.dpdns.org/"
  [chatwoot]="https://chatwoot.shopnoltd.dpdns.org/"
  [enketo]="https://enketo.shopnoltd.dpdns.org/"
  [n8n]="https://n8n.shopnoltd.dpdns.org/"
  [billing]="https://billing.shopnoltd.dpdns.org/health"
)

echo "================ HTTP STATUS + REDIRECTS ================"
for name in "${!SITES[@]}"; do
  url="${SITES[$name]}"
  code_and_loc=$(curl -sk -D - -o /dev/null --max-time 10 "$url" \
    | grep -Ei '^(HTTP/|location:)' | tr -d '\r' | tr '\n' ' ')
  printf "%-10s %-45s %s\n" "$name" "$url" "$code_and_loc"
done

echo
echo "================ POD HEALTH (known trouble spots) ================"
for ns_svc in \
  "shopno-apps:chatwoot" \
  "shopno-apps:enketo" \
  "shopno-apps:n8n" \
  "shopno-apps:gitea" \
  "toolbox:kpi" \
  "toolbox:kobocat" \
  "shopno-payments:billing-engine"
do
  ns="${ns_svc%%:*}"
  app="${ns_svc##*:}"
  echo "--- $ns / $app ---"
  kubectl -n "$ns" get pods -l "app=$app" -o wide 2>/dev/null \
    || kubectl -n "$ns" get pods 2>/dev/null | grep -i "$app"
done

echo
echo "================ GITEA INSTALL STATE CHECK ================"
kubectl -n shopno-apps exec deploy/gitea -- test -f /data/gitea/gitea.db \
  && echo "gitea.db EXISTS — install likely completed" \
  || echo "gitea.db MISSING — install wizard not completed yet"


echo
echo "================ RECENT ERROR LOGS (last 5 min) ================"
for ns_svc in "toolbox:kpi" "toolbox:kobocat" "shopno-apps:chatwoot" "shopno-apps:enketo"; do
  ns="${ns_svc%%:*}"
  app="${ns_svc##*:}"
  echo "--- $ns / $app errors ---"
  kubectl -n "$ns" logs -l "app=$app" --since=5m --tail=100 2>/dev/null \
    | grep -iE 'error|exception|traceback|5[0-9]{2}' | tail -20
done

echo
echo "Done. Review any non-200/302 codes and non-empty error blocks above."
