#!/usr/bin/env bash
# Full live status check for the Shopnoltd platform.
# Run from anywhere; only needs kubectl + docker configured.
set -uo pipefail

REGISTRY_OWNER="asaduzzamanbheramara-prog"

echo "###############################################"
echo "# 1. ALL PODS ACROSS ALL NAMESPACES"
echo "###############################################"
kubectl get pods -A -o wide

echo
echo "###############################################"
echo "# 2. PODS NOT RUNNING/READY (the actual problems)"
echo "###############################################"
kubectl get pods -A --field-selector=status.phase!=Running -o wide
echo "--- containers not Ready in Running pods ---"
kubectl get pods -A -o json | python3 -c "
import json,sys
data = json.load(sys.stdin)
for pod in data['items']:
    name = pod['metadata']['name']
    ns = pod['metadata']['namespace']
    statuses = pod.get('status', {}).get('containerStatuses', [])
    for c in statuses:
        if not c.get('ready', False):
            waiting = c.get('state', {}).get('waiting', {})
            reason = waiting.get('reason', 'unknown')
            print(f'{ns}/{name} -> container {c[\"name\"]} NOT READY: {reason}')
"

echo
echo "###############################################"
echo "# 3. DEPLOYMENTS: declared image vs replica health"
echo "###############################################"
kubectl get deployments -A -o json | python3 -c "
import json,sys
data = json.load(sys.stdin)
for d in data['items']:
    name = d['metadata']['name']
    ns = d['metadata']['namespace']
    desired = d['spec'].get('replicas', 1)
    ready = d.get('status', {}).get('readyReplicas', 0)
    images = [c['image'] for c in d['spec']['template']['spec']['containers']]
    status = 'OK' if ready >= desired else 'BROKEN'
    print(f'[{status}] {ns}/{name}: {ready}/{desired} ready | images: {images}')
"

echo
echo "###############################################"
echo "# 4. CONFIGMAPS: does tenant-router-config exist?"
echo "###############################################"
kubectl get configmap tenant-router-config -n default 2>&1

echo
echo "###############################################"
echo "# 5. GHCR: do the expected images actually exist?"
echo "###############################################"
for img in \
  "shopnoltd-api-service:v4" \
  "shopnoltd-billing-engine:v4" \
  "shopnoltd-oauth:v1" \
  "shopnoltd-frontend:latest" \
  "shopnoltd-freedomain-ui:v1" \
  "shopnoltd-ai:latest"
do
  full="ghcr.io/${REGISTRY_OWNER}/${img}"
  if docker manifest inspect "$full" > /dev/null 2>&1; then
    echo "[EXISTS]  $full"
  else
    echo "[MISSING] $full"
  fi
done

echo
echo "###############################################"
echo "# 6. Recent workflow-related git log (context)"
echo "###############################################"
git log --oneline -10 2>&1

echo
echo "###############################################"
echo "# DONE — paste this whole output back"
echo "###############################################"
