#!/bin/bash
# Verification script for Shopnoltd Kubernetes fixes

set -e

NAMESPACE_IDENTITY="shopno-identity"
NAMESPACE_DATA="shopno-data"

echo "============================================"
echo "Shopnoltd Deployment Fix Verification"
echo "============================================"
echo ""

# Check 1: PostgreSQL Status
echo "[1/6] Checking PostgreSQL..."
PG_STATUS=$(kubectl get pods -n "$NAMESPACE_DATA" -l app.kubernetes.io/name=postgres -o jsonpath='{.items[0].status.phase}')
PG_READY=$(kubectl get pods -n "$NAMESPACE_DATA" -l app.kubernetes.io/name=postgres -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}')
echo "  Status: $PG_STATUS"
echo "  Ready: $PG_READY"
if [ "$PG_READY" == "True" ]; then
    echo "  ✅ PostgreSQL READY"
else
    echo "  ❌ PostgreSQL NOT READY"
fi
echo ""

# Check 2: Auth-Service Status
echo "[2/6] Checking Auth-Service..."
AUTH_STATUS=$(kubectl get pods -n "$NAMESPACE_IDENTITY" -l app.kubernetes.io/name=auth-service -o jsonpath='{.items[0].status.phase}')
AUTH_READY=$(kubectl get pods -n "$NAMESPACE_IDENTITY" -l app.kubernetes.io/name=auth-service -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}')
echo "  Status: $AUTH_STATUS"
echo "  Ready: $AUTH_READY"
if [ "$AUTH_READY" == "True" ]; then
    echo "  ✅ Auth-Service READY"
else
    echo "  ❌ Auth-Service NOT READY"
fi
echo ""

# Check 3: Pod Restarts
echo "[3/6] Checking Pod Restarts..."
AUTH_RESTARTS=$(kubectl get pods -n "$NAMESPACE_IDENTITY" -l app.kubernetes.io/name=auth-service -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}')
echo "  Auth-Service restarts: $AUTH_RESTARTS"
if [ "$AUTH_RESTARTS" -lt 2 ]; then
    echo "  ✅ Low restart count (healthy)"
else
    echo "  ⚠️  Multiple restarts detected"
fi
echo ""

# Check 4: Database Connection
echo "[4/6] Testing Database Connection..."
DB_TEST=$(kubectl exec -n "$NAMESPACE_DATA" $(kubectl get pod -n "$NAMESPACE_DATA" -l app.kubernetes.io/name=postgres -o jsonpath='{.items[0].metadata.name}') -- pg_isready -U postgres 2>&1 || echo "failed")
echo "  Result: $DB_TEST"
if echo "$DB_TEST" | grep -q "accepting"; then
    echo "  ✅ Database accepting connections"
else
    echo "  ❌ Database connection failed"
fi
echo ""

# Check 5: Auth-Service Logs
echo "[5/6] Checking Auth-Service Startup Logs..."
LOGS=$(kubectl logs -n "$NAMESPACE_IDENTITY" $(kubectl get pod -n "$NAMESPACE_IDENTITY" -l app.kubernetes.io/name=auth-service -o jsonpath='{.items[0].metadata.name}') --tail=20)
if echo "$LOGS" | grep -q "db_initialized"; then
    echo "  ✅ Database initialized successfully"
elif echo "$LOGS" | grep -q "db_init_error"; then
    echo "  ⚠️  Database init error but app running (retrying)"
fi
if echo "$LOGS" | grep -q "Application startup complete"; then
    echo "  ✅ Application startup complete"
fi
echo ""

# Check 6: Health Endpoints
echo "[6/6] Testing Health Endpoints..."
POD_IP=$(kubectl get pod -n "$NAMESPACE_IDENTITY" -l app.kubernetes.io/name=auth-service -o jsonpath='{.items[0].status.podIP}')
if kubectl run -n "$NAMESPACE_IDENTITY" health-test --image=python:3.12-slim --restart=Never --rm -i -- python3 -c "
import urllib.request
import sys
try:
    resp = urllib.request.urlopen('http://$POD_IP:8080/healthz', timeout=5)
    if resp.status == 200:
        print('✅ /healthz OK')
    else:
        print('❌ /healthz failed:', resp.status)
except Exception as e:
    print('❌ /healthz error:', str(e))
" 2>/dev/null; then
    true
fi
echo ""

# Summary
echo "============================================"
echo "Summary:"
echo "============================================"
if [ "$PG_READY" == "True" ] && [ "$AUTH_READY" == "True" ]; then
    echo "✅ All systems OPERATIONAL"
    echo ""
    echo "Next steps:"
    echo "1. Deploy Redis service"
    echo "2. Test signup endpoint"
    echo "3. Deploy remaining services"
else
    echo "⚠️  Some issues detected"
    echo ""
    echo "Debug commands:"
    echo "  kubectl logs -f -n $NAMESPACE_IDENTITY deployment/auth-service"
    echo "  kubectl logs -f -n $NAMESPACE_DATA deployment/postgres"
    echo "  kubectl describe pod -n $NAMESPACE_IDENTITY -l app.kubernetes.io/name=auth-service"
fi
