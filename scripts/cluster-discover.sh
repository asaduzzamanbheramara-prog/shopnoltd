#!/usr/bin/env bash
echo "===================================================================="
echo "  CLUSTER DISCOVERY — $(date)"
echo "===================================================================="

echo -e "\n--- All Namespaces ---"
kubectl get namespaces

echo -e "\n--- All Deployments (every namespace) ---"
kubectl get deployments -A -o wide

echo -e "\n--- All Services (every namespace) ---"
kubectl get svc -A

echo -e "\n--- All Ingresses (every namespace) ---"
kubectl get ingress -A -o wide

echo -e "\n--- All Pods with Restart Counts (flag anything unstable) ---"
kubectl get pods -A -o wide

echo -e "\n--- Pods NOT Running/Ready (problems only) ---"
kubectl get pods -A --field-selector=status.phase!=Running
kubectl get pods -A -o json | jq -r '.items[] | select(.status.containerStatuses[]?.ready == false) | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null || echo "(jq not available, skipping ready-state filter)"

echo -e "\n===================================================================="
echo "  DISCOVERY COMPLETE"
echo "===================================================================="
