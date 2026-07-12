#!/usr/bin/env bash
# scripts/k8s-template.sh
# Creates a complete k8s base directory for a service.
# Usage: ./scripts/k8s-template.sh <service-name> <namespace> <image> <port>
# Example: ./scripts/k8s-template.sh api-service shopno-platform ghcr.io/shopnoltd/api-service 8080

set -euo pipefail

SERVICE="${1:?Usage: $0 <service-name> <namespace> <image> <port> <path-prefix>}"
NS="${2:?missing namespace}"
IMAGE="${3:?missing image}"
PORT="${4:?missing port}"
PREFIX="${5:-/}"

ROOT="k8s/services/${SERVICE}"
mkdir -p "${ROOT}"

# 1. kustomization.yaml
cat > "${ROOT}/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: ${NS}

resources:
  - namespace.yaml
  - serviceaccount.yaml
  - configmap.yaml
  - secret.yaml
  - pvc.yaml
  - deployment.yaml
  - service.yaml
  - ingress.yaml
  - hpa.yaml
  - networkpolicy.yaml
  - poddisruptionbudget.yaml
  - servicemonitor.yaml

commonLabels:
  app.kubernetes.io/name: ${SERVICE}
  app.kubernetes.io/part-of: shopnoltd
EOF

# 2. namespace.yaml
cat > "${ROOT}/namespace.yaml" <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: ${NS}
  labels:
    app.kubernetes.io/part-of: shopnoltd
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
EOF

# 3. serviceaccount.yaml
cat > "${ROOT}/serviceaccount.yaml" <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${SERVICE}
  namespace: ${NS}
automountServiceAccountToken: false
EOF

# 4. configmap.yaml
cat > "${ROOT}/configmap.yaml" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${SERVICE}-config
  namespace: ${NS}
data:
  APP_NAME: "${SERVICE}"
  APP_PORT: "${PORT}"
  LOG_LEVEL: "info"
  LOG_FORMAT: "json"
  ENV: "production"
  PATH_PREFIX: "${PREFIX}"
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://tempo.observability.svc.cluster.local:4317"
  REDIS_HOST: "redis.data.svc.cluster.local"
  REDIS_PORT: "6379"
  POSTGRES_HOST: "postgres.data.svc.cluster.local"
  POSTGRES_PORT: "5432"
  MINIO_ENDPOINT: "minio.data.svc.cluster.local:9000"
  KEYCLOAK_ISSUER: "https://auth.shopnoltd.com/realms/shopnoltd"
  KEYCLOAK_CLIENT_ID: "${SERVICE}"
EOF

# 5. secret.yaml (use sealed-secrets in production)
cat > "${ROOT}/secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: ${SERVICE}-secret
  namespace: ${NS}
type: Opaque
stringData:
  # Replace with sealed-secrets in production
  DATABASE_PASSWORD: "CHANGE_ME_DB_PASSWORD"
  REDIS_PASSWORD: "CHANGE_ME_REDIS_PASSWORD"
  MINIO_SECRET_KEY: "CHANGE_ME_MINIO_SECRET"
  KEYCLOAK_CLIENT_SECRET: "CHANGE_ME_KEYCLOAK_SECRET"
  JWT_SIGNING_KEY: "CHANGE_ME_JWT_KEY"
EOF

# 6. pvc.yaml
cat > "${ROOT}/pvc.yaml" <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ${SERVICE}-data
  namespace: ${NS}
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: gp3
  resources:
    requests:
      storage: 10Gi
EOF

# 7. deployment.yaml
cat > "${ROOT}/deployment.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${SERVICE}
  namespace: ${NS}
  labels:
    app.kubernetes.io/name: ${SERVICE}
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app.kubernetes.io/name: ${SERVICE}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: ${SERVICE}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "${PORT}"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: ${SERVICE}
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: ${SERVICE}
          image: ${IMAGE}:latest
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: ${PORT}
              protocol: TCP
          envFrom:
            - configMapRef:
                name: ${SERVICE}-config
            - secretRef:
                name: ${SERVICE}-secret
          env:
            - name: POD_NAME
              valueFrom: { fieldRef: { fieldPath: metadata.name } }
            - name: POD_NAMESPACE
              valueFrom: { fieldRef: { fieldPath: metadata.namespace } }
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
              ephemeral-storage: 256Mi
            limits:
              cpu: 1000m
              memory: 512Mi
              ephemeral-storage: 1Gi
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 30
          volumeMounts:
            - name: data
              mountPath: /var/lib/${SERVICE}
            - name: tmp
              mountPath: /tmp
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: ${SERVICE}-data
        - name: tmp
          emptyDir: {}
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: ${SERVICE}
EOF

# 8. service.yaml
cat > "${ROOT}/service.yaml" <<EOF
apiVersion: v1
kind: Service
metadata:
  name: ${SERVICE}
  namespace: ${NS}
  labels:
    app.kubernetes.io/name: ${SERVICE}
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP
  selector:
    app.kubernetes.io/name: ${SERVICE}
EOF

# 9. ingress.yaml
cat > "${ROOT}/ingress.yaml" <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ${SERVICE}
  namespace: ${NS}
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    traefik.ingress.kubernetes.io/router.tls: "true"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - ${SERVICE}.shopnoltd.com
      secretName: ${SERVICE}-tls
  rules:
    - host: ${SERVICE}.shopnoltd.com
      http:
        paths:
          - path: ${PREFIX}
            pathType: Prefix
            backend:
              service:
                name: ${SERVICE}
                port:
                  number: 80
EOF

# 10. hpa.yaml
cat > "${ROOT}/hpa.yaml" <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ${SERVICE}
  namespace: ${NS}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ${SERVICE}
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
    scaleUp:
      stabilizationWindowSeconds: 30
EOF

# 11. networkpolicy.yaml
cat > "${ROOT}/networkpolicy.yaml" <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ${SERVICE}
  namespace: ${NS}
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: ${SERVICE}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: shopno-ingress
        - namespaceSelector:
            matchLabels:
              name: shopno-platform
        - namespaceSelector:
            matchLabels:
              name: shopno-monitoring
      ports:
        - port: ${PORT}
          protocol: TCP
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: shopno-data
        - namespaceSelector:
            matchLabels:
              name: shopno-identity
        - namespaceSelector:
            matchLabels:
              name: shopno-monitoring
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - port: 53
          protocol: UDP
        - port: 443
          protocol: TCP
        - port: 5432
          protocol: TCP
        - port: 6379
          protocol: TCP
        - port: 9000
          protocol: TCP
EOF

# 12. poddisruptionbudget.yaml
cat > "${ROOT}/poddisruptionbudget.yaml" <<EOF
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ${SERVICE}
  namespace: ${NS}
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: ${SERVICE}
EOF

# 13. servicemonitor.yaml
cat > "${ROOT}/servicemonitor.yaml" <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ${SERVICE}
  namespace: ${NS}
  labels:
    app.kubernetes.io/name: ${SERVICE}
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: ${SERVICE}
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
      scrapeTimeout: 10s
EOF

echo ""
echo "✅ Created k8s base for ${SERVICE} in ${ROOT}"
echo "   Files:"
ls -1 "${ROOT}" | sed 's/^/     - /'
