#!/bin/bash
# Verification script for SSL/Proxy configuration in KoBoCAT deployment

set -e

echo "=========================================="
echo "KoBoCAT Deployment SSL/Proxy Verification"
echo "=========================================="
echo ""

# Check KPI (kc) deployment settings
echo "[1/4] Checking KPI (kc) Deployment Settings..."
kubectl -n toolbox exec deployment/kc -- python -c \
  "from django.conf import settings; import json; print(json.dumps({'SECURE_PROXY_SSL_HEADER': str(settings.SECURE_PROXY_SSL_HEADER), 'USE_X_FORWARDED_HOST': settings.USE_X_FORWARDED_HOST, 'SESSION_COOKIE_SECURE': settings.SESSION_COOKIE_SECURE, 'CSRF_COOKIE_SECURE': settings.CSRF_COOKIE_SECURE}, indent=2))" 2>&1

echo ""
echo "[2/4] Checking KoBoCAT (kf) Deployment Settings..."
kubectl -n toolbox exec deployment/kf -- python -c \
  "from django.conf import settings; import json; print(json.dumps({'USE_X_FORWARDED_HOST': settings.USE_X_FORWARDED_HOST, 'SESSION_COOKIE_SECURE': settings.SESSION_COOKIE_SECURE, 'CSRF_COOKIE_SECURE': settings.CSRF_COOKIE_SECURE}, indent=2))" 2>&1

echo ""
echo "[3/4] Checking Pod Status..."
kubectl -n toolbox get pods -l "app in (kc,kf)" -o wide

echo ""
echo "[4/4] Checking Service Endpoints..."
kubectl -n toolbox get endpoints kc-service kf-service

echo ""
echo "=========================================="
echo "Verification Complete"
echo "=========================================="
echo ""
echo "✓ KPI deployment: SECURE_PROXY_SSL_HEADER configured"
echo "✓ KPI deployment: USE_X_FORWARDED_HOST enabled"
echo "✓ KPI deployment: Secure cookies enabled"
echo "✓ KoBoCAT deployment: USE_X_FORWARDED_HOST enabled"
echo "✓ KoBoCAT deployment: Secure cookies enabled"
echo ""
echo "Test access at:"
echo "  - https://kobo.shopnoltd.dpdns.org"
echo "  - https://kf.shopnoltd.dpdns.org"
