$api = @"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api-service
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
  template:
    metadata:
      labels:
        app: api-service
    spec:
      containers:
      - name: api-service
        image: api-service:v4
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8080
        env:
        - name: REDIS_ADDR
          value: redis:6379
        - name: BILLING_SERVICE
          value: http://billing-engine:5000
        - name: OTEL_SERVICE_NAME
          value: api-service
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: http://otel-collector.observability.svc.cluster.local:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
        envFrom:
        - secretRef:
            name: oauth-secrets
        - secretRef:
            name: postgres-secret
        - secretRef:
            name: stripe-secret
        resources:
          requests:
            cpu: "100m"
            memory: "200Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
"@
Set-Content -Path "c:\Users\asadu\PROJECTS\shopnoltd\deployment-api-service.yaml" -Value $api -Encoding utf8

$billing = @"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: billing-engine
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: billing-engine
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
  template:
    metadata:
      labels:
        app: billing-engine
    spec:
      containers:
      - name: billing-engine
        image: billing-engine:v4
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 5000
        envFrom:
        - secretRef:
            name: stripe-secret
        env:
        - name: OTEL_SERVICE_NAME
          value: billing-engine
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: http://otel-collector.observability.svc.cluster.local:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "750m"
            memory: "768Mi"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 20
          periodSeconds: 10
          timeoutSeconds: 1
          failureThreshold: 3
          successThreshold: 1
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 1
          failureThreshold: 3
          successThreshold: 1
"@
Set-Content -Path "c:\Users\asadu\PROJECTS\shopnoltd\deployment-billing-engine.yaml" -Value $billing -Encoding utf8
Write-Output "Manifest rewrite complete"
