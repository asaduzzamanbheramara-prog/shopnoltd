#!/usr/bin/env bash
# ============================================================================
#  FULL PROJECT + ANDROID LIVE CHECK  (v2)
#  Run this on Shopnoltd-PC-1 (WSL), inside ~/PROJECTS/shopnoltd
# ============================================================================

PASS=0
FAIL=0
declare -a SUMMARY

mark_pass() { PASS=$((PASS+1)); SUMMARY+=("PASS  $1"); }
mark_fail() { FAIL=$((FAIL+1)); SUMMARY+=("FAIL  $1"); }

echo "===================================================================="
echo "  FULL PROJECT LIVE CHECK — $(date)"
echo "===================================================================="

# ---------------------------------------------------------------------------
echo -e "\n--- 1. Pods Not Running/Ready (real problems only) ---"
BAD_PODS=$(kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded 2>/dev/null)
echo "$BAD_PODS"
echo "(Completed = expected one-off jobs, not errors)"
if [ -z "$(echo "$BAD_PODS" | tail -n +2)" ]; then mark_pass "All pods Running/Succeeded"; else mark_fail "Some pods not Running/Succeeded"; fi

echo -e "\n--- 2. Pods With High Restart Counts (>5) ---"
HIGH_RESTARTS=$(kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{"  restarts="}{.status.containerStatuses[0].restartCount}{"\n"}{end}' | awk -F'restarts=' '$2+0 > 5 {print}')
echo "$HIGH_RESTARTS"
if [ -z "$HIGH_RESTARTS" ]; then mark_pass "No pods with excessive restarts"; else mark_fail "Pods with >5 restarts found"; fi

echo -e "\n--- 3. All Deployments Status ---"
kubectl get deployments -A

echo -e "\n--- 4. Named Deployment Checks (per-service) ---"
DEPLOYMENTS=(kc kf billing-engine tenant-router oauth-service chat freedomain-ui freedomain-website freedomain root-app postgres redis api api-service)
for dep in "${DEPLOYMENTS[@]}"; do
  for ns in default toolbox; do
    STATUS=$(kubectl get deployment "$dep" -n "$ns" -o jsonpath='{.status.readyReplicas}/{.status.replicas}' 2>/dev/null)
    if [ -n "$STATUS" ]; then
      echo "  $ns/$dep -> ready $STATUS"
      READY=$(echo "$STATUS" | cut -d/ -f1)
      TOTAL=$(echo "$STATUS" | cut -d/ -f2)
      if [ -n "$READY" ] && [ "$READY" = "$TOTAL" ] && [ "$TOTAL" != "0" ]; then
        mark_pass "$ns/$dep ready ($STATUS)"
      else
        mark_fail "$ns/$dep NOT fully ready ($STATUS)"
      fi
    fi
  done
done

# ---------------------------------------------------------------------------
echo -e "\n--- 5. All Ingress Hosts Discovered ---"
kubectl get ingress -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{":\n"}{range .spec.rules[*]}{"  host="}{.host}{"\n"}{end}{end}'

echo -e "\n--- 6. Ingress Controller Health ---"
kubectl get pods -n ingress-nginx -o jsonpath='{range .items[*]}{.metadata.name}{"  restarts="}{.status.containerStatuses[0].restartCount}{"  ready="}{.status.containerStatuses[0].ready}{"\n"}{end}'

echo -e "\n--- 7. End-to-End HTTP Checks (every discovered ingress host) ---"
HOSTS=$(kubectl get ingress -A -o jsonpath='{range .items[*]}{range .spec.rules[*]}{.host}{"\n"}{end}{end}' | sort -u)
for host in $HOSTS; do
  printf "%-40s " "$host"
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $host" http://localhost/ --max-time 10)
  echo "HTTP $CODE"
  if [[ "$CODE" =~ ^(200|301|302|401|403)$ ]]; then
    mark_pass "$host responded HTTP $CODE"
  else
    mark_fail "$host responded HTTP $CODE (or timed out)"
  fi
done

echo -e "\n--- 8. SSL Certificate Expiry Check (per host, port 443) ---"
for host in $HOSTS; do
  EXPIRY=$(echo | openssl s_client -servername "$host" -connect "$host:443" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
  if [ -n "$EXPIRY" ]; then
    echo "  $host -> expires $EXPIRY"
    EXP_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null)
    NOW_EPOCH=$(date +%s)
    if [ -n "$EXP_EPOCH" ] && [ "$EXP_EPOCH" -gt "$NOW_EPOCH" ]; then
      DAYS_LEFT=$(( (EXP_EPOCH - NOW_EPOCH) / 86400 ))
      if [ "$DAYS_LEFT" -lt 14 ]; then
        mark_fail "$host cert expires in $DAYS_LEFT days (renew soon)"
      else
        mark_pass "$host cert valid ($DAYS_LEFT days left)"
      fi
    else
      mark_fail "$host cert already expired or unreadable"
    fi
  else
    echo "  $host -> no cert found / connection failed (may be HTTP only)"
  fi
done

# ---------------------------------------------------------------------------
echo -e "\n--- 9. Toolbox: Direct Backend Checks (bypass ingress) ---"
echo -n "kc (KPI) :8000        "
KC=$(kubectl exec -n toolbox deployment/kc -- curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null)
echo "HTTP $KC"
[ "$KC" = "200" ] && mark_pass "kc backend HTTP 200" || mark_fail "kc backend HTTP $KC"

echo -n "kf (KoboCAT) :8000    "
KF=$(kubectl exec -n toolbox deployment/kf -- curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null)
echo "HTTP $KF"
[ "$KF" = "200" ] && mark_pass "kf backend HTTP 200" || mark_fail "kf backend HTTP $KF"

echo -e "\n--- 10. Datastore Connectivity ---"
check_db() {
  local ns=$1 dep=$2 cmd=$3 label=$4
  RESULT=$(kubectl exec -n "$ns" deployment/"$dep" -- $cmd 2>/dev/null)
  if [ $? -eq 0 ]; then
    echo "  $label -> OK"
    mark_pass "$label reachable"
  else
    echo "  $label -> FAILED"
    mark_fail "$label unreachable"
  fi
}
check_db default postgres pg_isready "default/postgres"
check_db default redis "redis-cli ping" "default/redis"
check_db toolbox postgres pg_isready "toolbox/postgres"
check_db toolbox redis "redis-cli ping" "toolbox/redis"
MONGO_OK=$(kubectl exec -n toolbox deployment/mongo -- mongosh --quiet --eval "db.adminCommand('ping')" 2>/dev/null || kubectl exec -n toolbox deployment/mongo -- mongo --quiet --eval "db.adminCommand('ping')" 2>/dev/null)
if [ -n "$MONGO_OK" ]; then mark_pass "toolbox/mongo reachable"; else mark_fail "toolbox/mongo unreachable"; fi

# ---------------------------------------------------------------------------
echo -e "\n--- 11. Disk / PVC Usage (postgres-data etc. don't grow unbounded) ---"
kubectl get pvc -A
echo ""
for ns in default toolbox; do
  for dep in postgres mongo; do
    echo "  $ns/$dep disk usage:"
    kubectl exec -n "$ns" deployment/"$dep" -- df -h 2>/dev/null | grep -E "data|Filesystem" || echo "    (could not read)"
  done
done

# ---------------------------------------------------------------------------
echo -e "\n--- 12. Meet (Jitsi) Stack ---"
kubectl get pods -n meet -o jsonpath='{range .items[*]}{.metadata.name}{"  ready="}{.status.containerStatuses[0].ready}{"\n"}{end}'

echo -e "\n--- 13. Monitoring Stack ---"
kubectl get pods -n monitoring -o jsonpath='{range .items[*]}{.metadata.name}{"  ready="}{.status.containerStatuses[0].ready}{"\n"}{end}'

# ---------------------------------------------------------------------------
echo -e "\n--- 14. Recent Error Logs (last 50 lines, filtered) per key deployment ---"
for dep in kc kf tenant-router oauth-service chat billing-engine; do
  for ns in default toolbox; do
    LOGS=$(kubectl logs -n "$ns" deployment/"$dep" --tail=50 2>/dev/null | grep -iE "error|exception|traceback|fatal|panic")
    if [ -n "$LOGS" ]; then
      echo "  [$ns/$dep] recent errors:"
      echo "$LOGS" | sed 's/^/    /'
      mark_fail "$ns/$dep has recent errors in logs"
    fi
  done
done

# ---------------------------------------------------------------------------
echo -e "\n--- 15. Android APK / Mobile Backend Check ---"
if [ -d "./apks" ]; then
  echo "Found apks/ directory:"
  ls -la ./apks
  APK_FILE=$(find ./apks -name "*.apk" | head -n 1)
  if [ -n "$APK_FILE" ]; then
    echo "  Inspecting: $APK_FILE"
    if command -v aapt >/dev/null 2>&1; then
      echo "  --- Package info (aapt) ---"
      aapt dump badging "$APK_FILE" | grep -E "package:|versionName|versionCode|targetSdkVersion|uses-permission"
    else
      echo "  aapt not installed — skipping manifest inspection."
      echo "  Install with: sudo apt install aapt  (or use 'apkanalyzer' from Android SDK)"
    fi
    echo "  --- Hardcoded URLs inside APK (grep strings) ---"
    unzip -p "$APK_FILE" classes.dex 2>/dev/null | strings | grep -Eo "https?://[a-zA-Z0-9./_-]+" | sort -u | head -30
  else
    echo "  No .apk file found inside apks/"
  fi
else
  echo "  No apks/ directory found in current path — skipping APK inspection."
fi

echo ""
echo "  If you know the mobile app's API base URL(s), test them directly below:"
echo "  (edit MOBILE_API_HOSTS array in this script to add real hosts)"
MOBILE_API_HOSTS=()   # <-- fill in e.g. ("api.shopnoltd.com" "kf.shopnoltd.com")
for host in "${MOBILE_API_HOSTS[@]}"; do
  printf "%-40s " "$host"
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$host/" --max-time 10)
  echo "HTTPS $CODE"
  [[ "$CODE" =~ ^(200|301|302|401|403)$ ]] && mark_pass "mobile API $host reachable" || mark_fail "mobile API $host HTTP $CODE"
done

# ---------------------------------------------------------------------------
echo -e "\n===================================================================="
echo "  SUMMARY:  $PASS passed / $FAIL failed"
echo "===================================================================="
for line in "${SUMMARY[@]}"; do
  echo "  $line"
done

echo -e "\n===================================================================="
echo "  CHECK COMPLETE — $(date)"
echo "===================================================================="
