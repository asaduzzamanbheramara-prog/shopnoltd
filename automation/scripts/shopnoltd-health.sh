#!/usr/bin/env bash
set -euo pipefail

echo "================================="
echo " Shopnoltd Platform Health Check "
echo "================================="

echo
echo "Namespaces"
kubectl get ns

echo
echo "Deployments"
kubectl get deploy -A

echo
echo "Pods"
kubectl get pods -A

echo
echo "Services"
kubectl get svc -A

echo
echo "Ingress"
kubectl get ingress -A

echo
echo "PVC"
kubectl get pvc -A

echo
echo "Certificates"
kubectl get certificate -A 2>/dev/null || true

echo
echo "Events"
kubectl get events -A --sort-by=.lastTimestamp | tail -50
