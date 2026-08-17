#!/bin/bash
set -e

echo "=== DEPLOYING MINIMAL AUTH STACK ==="

# 1. Deploy postgres (data layer)
echo "1. Deploying postgres..."
kubectl apply -f k8s/services/postgres/service.yaml
kubectl apply -f k8s/services/postgres/configmap.yaml
kubectl apply -f k8s/services/postgres/secret.yaml
kubectl apply -f k8s/services/postgres/pvc.yaml
kubectl apply -f k8s/services/postgres/deployment.yaml

echo "   Waiting for postgres to be Ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgres -n shopno-data --timeout=120s 2>/dev/null || \
  echo "   ⚠ Postgres pod still starting (may need extra time)"

# 2. Deploy keycloak (identity provider)
echo "2. Deploying keycloak..."
kubectl apply -f k8s/services/keycloak/service.yaml
kubectl apply -f k8s/services/keycloak/configmap.yaml
kubectl apply -f k8s/services/keycloak/secret.yaml
kubectl apply -f k8s/services/keycloak/pvc.yaml
kubectl apply -f k8s/services/keycloak/deployment.yaml

echo "   Waiting for keycloak to be Ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=keycloak -n shopno-identity --timeout=120s 2>/dev/null || \
  echo "   ⚠ Keycloak pod still starting (may need extra time)"

# 3. Deploy auth-service WITH THE CONFIG FIX
echo "3. Deploying auth-service (with Keycloak internal DNS fix)..."
kubectl apply -f k8s/services/auth-service/service.yaml
kubectl apply -f k8s/services/auth-service/configmap.yaml
kubectl apply -f k8s/services/auth-service/secret.yaml
kubectl apply -f k8s/services/auth-service/pvc.yaml
kubectl apply -f k8s/services/auth-service/deployment.yaml

echo "   Waiting for auth-service to be Ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=auth-service -n shopno-identity --timeout=120s 2>/dev/null || \
  echo "   ⚠ Auth-service pod still starting"

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo ""
echo "Checking pod status..."
echo ""
echo "Postgres:"
kubectl get pods -n shopno-data -l app.kubernetes.io/name=postgres
echo ""
echo "Keycloak:"
kubectl get pods -n shopno-identity -l app.kubernetes.io/name=keycloak
echo ""
echo "Auth-Service:"
kubectl get pods -n shopno-identity -l app.kubernetes.io/name=auth-service
echo ""
echo "=== TESTING AUTH ENDPOINTS ==="
echo ""
echo "Test 1: Signup (POST /api/v1/auth/signup)"
curl -s -w "HTTP: %{http_code}\n" -X POST \
  "https://auth-service.shopnoltd.dpdns.org/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@shopnoltd.dpdns.org","password":"TestPass1234!"}'

echo ""
echo "Test 2: Login (POST /api/v1/auth/login)"
curl -s -w "HTTP: %{http_code}\n" -X POST \
  "https://auth-service.shopnoltd.dpdns.org/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@shopnoltd.dpdns.org","password":"TestPass1234!"}'
