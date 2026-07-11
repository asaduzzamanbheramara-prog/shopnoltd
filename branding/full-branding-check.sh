#!/bin/bash
set -e

echo "======================================"
echo "KPI"
echo "======================================"

kubectl exec -n toolbox deployment/kc -- sh -c '
echo "--- Logo files ---"
find /srv/src/kpi \
    \( -iname "*logo*" -o -iname "*kobo*" -o -iname "*shopno*" -o -iname "*favicon*" \) \
    2>/dev/null

echo
echo "--- Remaining Kobo branding ---"
grep -RniE "KoboToolbox|Kobo Collect|KoboCollect|kobologo|form-logo" \
/srv/src/kpi 2>/dev/null | head -200

echo
echo "--- Shopnoltd branding ---"
grep -RniE "Shopnoltd|ShopnoltdToolbox|shopnoltdlogo" \
/srv/src/kpi 2>/dev/null | head -200
'

echo
echo "======================================"
echo "KOBOCAT"
echo "======================================"

kubectl exec -n toolbox deployment/kf -- sh -c '
echo "--- Logo files ---"
find /srv/src/kobocat \
    \( -iname "*logo*" -o -iname "*kobo*" -o -iname "*shopno*" -o -iname "*favicon*" \) \
    2>/dev/null

echo
echo "--- Remaining Kobo branding ---"
grep -RniE "KoboToolbox|Kobo Collect|KoboCollect|kobologo|form-logo" \
/srv/src/kobocat 2>/dev/null | head -200

echo
echo "--- Shopnoltd branding ---"
grep -RniE "Shopnoltd|ShopnoltdToolbox|shopnoltdlogo" \
/srv/src/kobocat 2>/dev/null | head -200
'

echo
echo "======================================"
echo "ENKETO"
echo "======================================"

kubectl exec -n toolbox deployment/ee -- sh -c '
echo "--- Logo files ---"
find /srv/src/enketo \
    \( -iname "*logo*" -o -iname "*icon*" -o -iname "*shopno*" -o -iname "*favicon*" \) \
    2>/dev/null

echo
echo "--- Remaining Kobo branding ---"
grep -RniE "KoboToolbox|Kobo Collect|KoboCollect|kobologo|form-logo" \
/srv/src/enketo 2>/dev/null | head -200

echo
echo "--- Shopnoltd branding ---"
grep -RniE "Shopnoltd|ShopnoltdToolbox|shopnoltdlogo" \
/srv/src/enketo 2>/dev/null | head -200
'

echo
echo "======================================"
echo "DEPLOYMENT IMAGES"
echo "======================================"

kubectl get deployment -n toolbox \
-o custom-columns=NAME:.metadata.name,IMAGE:.spec.template.spec.containers[*].image

echo
echo "======================================"
echo "IMAGE DIGESTS"
echo "======================================"

kubectl exec -n toolbox deployment/kc -- sha256sum /srv/src/kpi/static/kobologo.svg 2>/dev/null || true
kubectl exec -n toolbox deployment/kf -- sha256sum /srv/src/kobocat/onadata/static/images/kobologo.svg 2>/dev/null || true
