#!/usr/bin/env bash
echo "===================================================================="
echo "  FULL PROJECT LIVE CHECK — $(date)"
echo "===================================================================="

echo -e "\n--- 1. Pods Not Running/Ready (real problems only) ---"
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded 2>/dev/null
echo "(pods with status=Completed are expected one-off jobs, not errors)"

echo -e "\n--- 2. Pods With High Restart Counts (possible instability) ---"
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{"  restarts="}{.status.containerStatuses[0].restartCount}{"\n"}{end}' | awk -F'restarts=' '$2+0 > 5 {print}'

echo -e "\n--- 3. All Deployments Status ---"
kubectl get deployments -A

echo -e "\n--- 4. All Ingress Hosts Discovered ---"
kubectl get ingress -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{":\n"}{range .spec.rules[*]}{"  host="}{.host}{"\n"}{end}{end}'

echo -e "\n--- 5. Ingress Controller Health ---"
kubectl get pods -n ingress-nginx -o jsonpath='{range .items[*]}{.metadata.name}{"  restarts="}{.status.containerStatuses[0].restartCount}{"  ready="}{.status.containerStatuses[0].ready}{"\n"}{end}'

echo -e "\n--- 6. End-to-End HTTP Checks (every discovered ingress host) ---"
HOSTS=$(kubectl get ingress -A -o jsonpath='{range .items[*]}{range .spec.rules[*]}{.host}{"\n"}{end}{end}' | sort -u)
for host in $HOSTS; do
  printf "%-40s " "$host"
  curl -s -o /dev/null -w "HTTP %{http_code}  (%{time_total}s)\n" -H "Host: $host" http://localhost/ --max-time 10
done

echo -e "\n--- 7. Toolbox: Direct Backend Checks (bypass ingress) ---"
echo -n "kc (KPI) :8000        "
kubectl exec -n toolbox deployment/kc -- curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/ 2>/dev/null || echo "FAILED"
echo -n "kf (KoboCAT) :8000    "
kubectl exec -n toolbox deployment/kf -- curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/ 2>/dev/null || echo "FAILED"

echo -e "\n--- 8. Datastore Connectivity ---"
echo "-- default/postgres --"
kubectl exec -n default deployment/postgres -- pg_isready 2>/dev/null || echo "  FAILED"
echo "-- default/redis --"
kubectl exec -n default deployment/redis -- redis-cli ping 2>/dev/null || echo "  FAILED"
echo "-- toolbox/postgres --"
kubectl exec -n toolbox deployment/postgres -- pg_isready 2>/dev/null || echo "  FAILED"
echo "-- toolbox/redis --"
kubectl exec -n toolbox deployment/redis -- redis-cli ping 2>/dev/null || echo "  FAILED"
echo "-- toolbox/mongo --"
kubectl exec -n toolbox deployment/mongo -- mongosh --quiet --eval "db.adminCommand('ping')" 2>/dev/null || kubectl exec -n toolbox deployment/mongo -- mongo --quiet --eval "db.adminCommand('ping')" 2>/dev/null || echo "  FAILED"

echo -e "\n--- 9. Meet (Jitsi) Stack ---"
kubectl get pods -n meet -o jsonpath='{range .items[*]}{.metadata.name}{"  ready="}{.status.containerStatuses[0].ready}{"\n"}{end}'

echo -e "\n--- 10. Monitoring Stack ---"
kubectl get pods -n monitoring -o jsonpath='{range .items[*]}{.metadata.name}{"  ready="}{.status.containerStatuses[0].ready}{"\n"}{end}'

echo -e "\n===================================================================="
echo "  CHECK COMPLETE"
echo "===================================================================="
