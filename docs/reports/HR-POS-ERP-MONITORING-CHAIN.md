# Shopnoltd HR → POS → POS Billing → ERP → Monitoring Chain

## Verification contract

This document defines the production verification contract for the business/observability chain. A component is complete only when implementation, routing, monitoring, GitOps inclusion, and automated smoke verification are all present.

## Required chain

1. HR
2. POS
3. POS Billing
4. ERP
5. Metrics/exporters
6. ServiceMonitors
7. Prometheus
8. Prometheus alert rules
9. Alertmanager
10. Grafana dashboards
11. Ingress/DNS
12. ArgoCD/Kustomize
13. CI smoke/E2E

## Completion rules

- Website-builder definitions are not considered backend implementations by themselves.
- Every production service must expose a deterministic health endpoint and metrics where supported.
- Monitoring resources must be included by the active Kustomize root and therefore reconciled by ArgoCD.
- Alert rules must have an Alertmanager route/receiver path and a corresponding dashboard or operational view where useful.
- Public ingress hosts must resolve to the intended service and use the platform TLS strategy.
- CI must fail when an essential public health endpoint is unavailable.
- Post-deployment verification must run after the image-promotion/deployment path and on relevant Kubernetes changes.

## Existing automation baseline

The repository already contains a post-deployment smoke workflow that waits for reconciliation and polls required public endpoints until healthy. Keep this as a release gate and extend its matrix whenever a new essential production service is introduced.

## Outstanding implementation policy

If HR, POS, POS Billing, or ERP are only represented by frontend website types, they must not be reported as fully operational backend services. Add the missing service/API/deployment wiring only where an actual backend is intended; otherwise expose them as application templates and ensure their documented capabilities do not claim unavailable backend functionality.

## Operational status

This file is a verification contract, not a claim that the live cluster is currently healthy. Live Kubernetes/ArgoCD state must be verified by the deployment environment or CI smoke workflow.
