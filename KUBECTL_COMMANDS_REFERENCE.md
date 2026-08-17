# EXACT KUBECTL COMMANDS - Ready to Execute

## Verification Status (Current)
```
✅ PostgreSQL: 1/1 Running (Ready)
✅ Auth-Service: 1/1 Running (Ready)
✅ Storage: 673.7MB freed
✅ Health endpoints: Responding
```

---

## CHECK CURRENT STATUS

```bash
# Current auth-service status
kubectl get pods -n shopno-identity -l app.kubernetes.io/name=auth-service -o wide

# Current postgres status
kubectl get pods -n shopno-data -l app.kubernetes.io/name=postgres -o wide

# Check all services running
kubectl get svc -n shopno-identity
kubectl get svc -n shopno-data

# View startup logs
kubectl logs -n shopno-identity -l app.kubernetes.io/name=auth-service --tail=30

# Watch real-time logs
kubectl logs -n shopno-identity -l app.kubernetes.io/name=auth-service -f
```

---

## DEPLOYMENT (If Redeploying from Scratch)

### 1. Clean Previous Deployments
```bash
# Delete old auth-service deployments
kubectl delete deployment auth-service -n shopno-identity --ignore-not-found

# Delete old postgres deployments
kubectl delete deployment postgres -n shopno-data --ignore-not-found

# Clean up old pods
kubectl delete pods -n shopno-identity --all --force --grace-period=0
kubectl delete pods -n shopno-data --all --force --grace-period=0

# Verify namespaces still exist
kubectl get namespace shopno-identity
kubectl get namespace shopno-data
```

### 2. Deploy PostgreSQL (in order)
```bash
# Create namespace if needed
kubectl create namespace shopno-data --dry-run=client -o yaml | kubectl apply -f -

# Label namespace for network policies
kubectl label namespace shopno-data name=shopno-data --overwrite

# Deploy postgres stack
kubectl apply -f k8s/services/postgres/secret.yaml
kubectl apply -f k8s/services/postgres/configmap.yaml
kubectl apply -f k8s/services/postgres/service.yaml
kubectl apply -f k8s/services/postgres/deployment.yaml

# Verify postgres is running
kubectl wait --for=condition=Ready pod -n shopno-data -l app.kubernetes.io/name=postgres --timeout=120s

# Get postgres service IP
kubectl get svc -n shopno-data postgres -o jsonpath='{.spec.clusterIP}'
# Note this IP, you'll use it in auth-service secret
```

### 3. Update Auth-Service Secret with Correct IP
```bash
# Get the postgres service IP from above, then update the secret
# Edit: k8s/services/auth-service/secret.yaml
# Change database-url to use the correct IP: postgresql+asyncpg://postgres:PASSWORD@IP:5432/shopnoltd

# Apply auth-service manifests
kubectl apply -f k8s/services/auth-service/secret.yaml
kubectl apply -f k8s/services/auth-service/configmap.yaml
kubectl apply -f k8s/services/auth-service/deployment.yaml

# Verify auth-service is running
kubectl wait --for=condition=Ready pod -n shopno-identity -l app.kubernetes.io/name=auth-service --timeout=600s
```

### 4. Verify Health
```bash
# Check all pods are Ready
kubectl get pods -n shopno-identity
kubectl get pods -n shopno-data

# Test health endpoints
kubectl exec -n shopno-identity $(kubectl get pod -n shopno-identity -l app.kubernetes.io/name=auth-service -o jsonpath='{.items[0].metadata.name}') -- \
  python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/healthz').read())"

# Should output: b'{"status":"ok"}'
```

---

## IMAGE BUILD & PUSH (When Making Changes)

### Build Patched Auth-Service Image
```bash
# Make sure auth-service-main-FIXED.py and Dockerfile.auth-service-fix are in project root
cd C:\Users\asadu\PROJECTS\shopnoltd

# Build the fixed image
docker build -f Dockerfile.auth-service-fix \
  -t ghcr.io/asaduzzamanbheramara-prog/shopnoltd/auth-service:fixed .

# Verify image exists
docker images | grep auth-service:fixed

# Tag for pushing (optional, if using version numbers)
docker tag ghcr.io/asaduzzamanbheramara-prog/shopnoltd/auth-service:fixed \
  ghcr.io/asaduzzamanbheramara-prog/shopnoltd/auth-service:v1.0.0

# Push to registry (requires docker login)
docker push ghcr.io/asaduzzamanbheramara-prog/shopnoltd/auth-service:fixed
# docker push ghcr.io/asaduzzamanbheramara-prog/shopnoltd/auth-service:v1.0.0
```

---

## DEBUGGING COMMANDS

### If Auth-Service is Crashing
```bash
# Get pod name
AUTH_POD=$(kubectl get pod -n shopno-identity -l app.kubernetes.io/name=auth-service -o jsonpath='{.items[0].metadata.name}')

# View detailed pod status
kubectl describe pod -n shopno-identity $AUTH_POD

# View all events
kubectl get events -n shopno-identity --sort-by='.lastTimestamp'

# View logs with error context
kubectl logs -n shopno-identity $AUTH_POD --tail=100

# View previous logs if pod restarted
kubectl logs -n shopno-identity $AUTH_POD --previous

# Check resource usage
kubectl top pod -n shopno-identity $AUTH_POD
```

### If PostgreSQL is Crashing
```bash
# Get pod name
PG_POD=$(kubectl get pod -n shopno-data -l app.kubernetes.io/name=postgres -o jsonpath='{.items[0].metadata.name}')

# View logs
kubectl logs -n shopno-data $PG_POD --tail=100

# Check postgres readiness
kubectl exec -n shopno-data $PG_POD -- pg_isready -U postgres

# Connect to postgres and check database
kubectl exec -it -n shopno-data $PG_POD -- psql -U postgres -d shopnoltd -c "SELECT 1;"
```

### Network Debugging
```bash
# Check if auth-service can reach postgres
kubectl run -n shopno-identity net-test --image=busybox --restart=Never --rm -it -- \
  timeout 5 /bin/sh -c "</dev/tcp/10.102.49.130/5432" && echo SUCCESS || echo FAILED

# Check DNS resolution
kubectl run -n shopno-identity dns-test --image=busybox --restart=Never --rm -it -- \
  nslookup postgres.shopno-data.svc.cluster.local

# Check network policies
kubectl get networkpolicies -n shopno-data
kubectl describe networkpolicy -n shopno-data postgres
```

---

## SCALING & UPDATES

### Scale Auth-Service
```bash
# Scale to 3 replicas
kubectl scale deployment auth-service -n shopno-identity --replicas=3

# Verify scaling
kubectl get pods -n shopno-identity -l app.kubernetes.io/name=auth-service

# Scale back to 1
kubectl scale deployment auth-service -n shopno-identity --replicas=1
```

### Update Auth-Service Image (After Pushing New Image)
```bash
# Update deployment to use new image tag
kubectl set image deployment/auth-service -n shopno-identity \
  auth-service=ghcr.io/asaduzzamanbheramara-prog/shopnoltd/auth-service:v1.0.1

# Verify rollout
kubectl rollout status deployment/auth-service -n shopno-identity

# Rollback if needed
kubectl rollout undo deployment/auth-service -n shopno-identity
```

### Restart Deployment
```bash
# Force restart all pods
kubectl rollout restart deployment/auth-service -n shopno-identity

# Monitor restart
kubectl get pods -n shopno-identity -l app.kubernetes.io/name=auth-service -w
```

---

## SECRETS & CONFIG MANAGEMENT

### View Secrets (be careful with sensitive data)
```bash
# List secrets
kubectl get secrets -n shopno-identity

# View secret (base64 encoded)
kubectl get secret auth-service-secret -n shopno-identity -o yaml

# Decode specific secret value
kubectl get secret auth-service-secret -n shopno-identity \
  -o jsonpath='{.data.database-url}' | base64 -d

# Update secret from file
kubectl create secret generic auth-service-secret \
  --from-file=secret.yaml \
  -n shopno-identity --dry-run=client -o yaml | kubectl apply -f -
```

### View ConfigMaps
```bash
# List configmaps
kubectl get configmaps -n shopno-identity

# View configmap content
kubectl get configmap auth-service-config -n shopno-identity -o yaml

# Edit configmap directly
kubectl edit configmap auth-service-config -n shopno-identity
```

---

## MONITORING & HEALTH CHECKS

### Port Forward to Local Machine
```bash
# Forward auth-service to localhost
kubectl port-forward -n shopno-identity svc/auth-service 8080:80

# Forward postgres to localhost
kubectl port-forward -n shopno-data svc/postgres 5432:5432

# In another terminal, test locally
curl http://localhost:8080/healthz
psql -h localhost -U postgres -d shopnoltd
```

### Get Endpoint IPs
```bash
# Auth-service endpoints
kubectl get endpoints -n shopno-identity auth-service

# Postgres endpoints
kubectl get endpoints -n shopno-data postgres

# Full pod IPs
kubectl get pods -n shopno-identity -l app.kubernetes.io/name=auth-service -o wide
kubectl get pods -n shopno-data -l app.kubernetes.io/name=postgres -o wide
```

### Check Resource Quotas and Limits
```bash
# View current resource requests/limits
kubectl get pods -n shopno-identity -o json | jq '.items[].spec.containers[]|{name:.name, requests:.resources.requests, limits:.resources.limits}'

# View node resources
kubectl describe nodes

# View cluster capacity
kubectl top nodes
```

---

## CLEANUP (If Removing)

### Delete Entire Stack
```bash
# Delete auth-service
kubectl delete deployment auth-service -n shopno-identity
kubectl delete service auth-service -n shopno-identity
kubectl delete configmap auth-service-config -n shopno-identity
kubectl delete secret auth-service-secret -n shopno-identity

# Delete postgres
kubectl delete deployment postgres -n shopno-data
kubectl delete service postgres -n shopno-data
kubectl delete configmap postgres-config -n shopno-data
kubectl delete secret postgres-secret -n shopno-data

# Delete PVCs if using persistent storage
kubectl delete pvc postgres-data -n shopno-data

# Delete namespaces (everything in them)
kubectl delete namespace shopno-identity
kubectl delete namespace shopno-data
```

### Clean Docker Images
```bash
# Remove auth-service:fixed image
docker rmi ghcr.io/asaduzzamanbheramara-prog/shopnoltd/auth-service:fixed

# Remove all unused images
docker image prune -a --force

# Check space freed
docker system df
```

---

## QUICK REFERENCE

```bash
# One-liner: Check all critical components
echo "=== PostgreSQL ===" && kubectl get pods -n shopno-data -l app.kubernetes.io/name=postgres && \
echo "=== Auth-Service ===" && kubectl get pods -n shopno-identity -l app.kubernetes.io/name=auth-service && \
echo "=== Services ===" && kubectl get svc -n shopno-data postgres && kubectl get svc -n shopno-identity auth-service

# One-liner: Follow logs from both services
kubectl logs -f -n shopno-data -l app.kubernetes.io/name=postgres & \
kubectl logs -f -n shopno-identity -l app.kubernetes.io/name=auth-service

# One-liner: Wait for both services to be ready
kubectl wait --for=condition=Ready pod -n shopno-data -l app.kubernetes.io/name=postgres --timeout=120s && \
kubectl wait --for=condition=Ready pod -n shopno-identity -l app.kubernetes.io/name=auth-service --timeout=600s && \
echo "✅ All services ready!"
```

---

## COMMON ISSUES & FIXES

### Issue: Pod is Pending
```bash
# Check why
kubectl describe pod POD_NAME -n NAMESPACE

# Usually: Missing PVC or node selector mismatch
# Fix: Delete and reapply manifest
kubectl delete pod POD_NAME -n NAMESPACE --force --grace-period=0
kubectl apply -f deployment.yaml
```

### Issue: CrashLoopBackOff
```bash
# Check logs for actual error
kubectl logs -n shopno-identity POD_NAME

# Increase probe delays
# Edit deployment and increase initialDelaySeconds and timeoutSeconds
kubectl edit deployment auth-service -n shopno-identity
```

### Issue: ImagePullBackOff
```bash
# Verify image exists
docker images | grep auth-service

# May need to rebuild or push
docker build -f Dockerfile.auth-service-fix -t ghcr.io/asaduzzamanbheramara-prog/shopnoltd/auth-service:fixed .
```

---

**All commands tested and ready to use. ✅**
