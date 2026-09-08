# Shopnoltd Observability Release Gate

The GitOps source of truth now includes a production observability stack under `k8s/services/observability`.

## Components

- Prometheus 3.14.0
- Alertmanager 0.33.1
- Grafana 13.2.1
- Loki 3.7.4
- Grafana Alloy 1.19.2 for Kubernetes pod logs and cluster events
- kube-state-metrics 2.20.0
- Prometheus node-exporter 1.12.1
- Metrics Server 0.9.0, managed from its pinned upstream release manifest

## Data flow

- Kubernetes workload metrics -> Prometheus
- Kubernetes object state -> kube-state-metrics -> Prometheus
- Host metrics -> node-exporter -> Prometheus
- Kubernetes pod logs/events -> Grafana Alloy -> Loki
- Prometheus alerts -> Alertmanager
- Prometheus and Loki -> Grafana provisioned datasources

## Security and durability

- Monitoring data uses persistent PVCs for Prometheus, Alertmanager, Loki, and Grafana.
- Prometheus Kubernetes discovery uses a dedicated read-only ClusterRole.
- kube-state-metrics and Alloy use dedicated service accounts and least-privilege read access.
- Prometheus, Alertmanager, and Loki remain ClusterIP-only; only Grafana is published through the browser-facing monitoring ingress.
- No runtime credentials are committed to Git.

## Runtime release gate

After ArgoCD synchronization, verify:

1. `kubectl top nodes` and `kubectl top pods` work through Metrics Server.
2. Prometheus is ready and discovers application, kube-state-metrics, and node-exporter targets.
3. Alertmanager is ready and receives a controlled test alert.
4. Grafana is reachable and shows both Prometheus and Loki datasources as healthy.
5. Loki receives recent Shopnoltd application logs and Kubernetes events.
6. Crash-loop, target-down, readiness, memory, and filesystem alerts evaluate correctly.
7. HPA metrics remain available after observability changes.
8. Monitoring remains healthy while AI, payments, communications, social, remote-device, and database workloads are exercised.
