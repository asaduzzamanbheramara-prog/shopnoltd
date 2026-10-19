# Codespaces zero-replica service preflight

Status: **preflight only — not a production migration or deployment**.

## Goal

Use GitHub-hosted CI to establish whether the three Python services below can be built from the repository while leaving the currently declared production replica count unchanged:

- `interior-service`
- `license-service`
- `training-service`

The workflow `.github/workflows/codespaces-zero-replica-preflight.yml` verifies each service's source files, confirms the corresponding checked-in Deployment manifest still declares `replicas: 0`, and builds the image without publishing it.

## What a PASS proves

- The selected Docker build completes from the checked-out commit.
- Required source files exist.
- The source manifest still declares zero replicas at the tested commit.

## What a PASS does not prove

- The live cluster has zero replicas or matches the repository manifest.
- A container can start and become ready.
- PostgreSQL, Redis, PVCs, secrets, queues, ingress, or provider dependencies are available.
- A service has been deployed to a Codespace, or that it can remain running when the Codespace stops.
- Production traffic has moved away from the PC-hosted K3s cluster.

Each service's application startup calls dependency checks for PostgreSQL and Redis and runs SQLAlchemy metadata creation. Do not start these services against production dependencies for a smoke test. A separate isolated test stack with disposable PostgreSQL and Redis, test-only credentials, and explicit cleanup is required before runtime testing.

## Safety and rollout rules

1. Keep the production K3s cluster and public routing unchanged until migration acceptance and rollback checks pass.
2. Never commit or copy production kubeconfig, Kubernetes Secret values, database passwords, Cloudflare credentials, or production user data into Codespaces, Actions logs, artifacts, or this repository.
3. Do not set production replicas above zero through this workflow. It has no Kubernetes credentials and no deployment/publish step.
4. Before moving any workload, inventory its live effective replica count, PVC/data dependencies, service-to-service dependencies, required environment variable **names** (not values), resource needs, ingress, restart behavior, and rollback.
5. GitHub Actions runners are ephemeral and Codespaces can stop when idle. Neither is a durable always-on production runtime. GHCR distributes images; it does not run them.
6. To meet the requirement that production continues while the PC/server is passive, select and validate a durable runtime with persistent storage and networking, then migrate one service at a time. Do not represent this preflight as completion of that migration.

## Acceptance gates

- [ ] Workflow passes for all three service builds.
- [ ] A dedicated isolated PostgreSQL + Redis test environment starts each service and passes `/healthz` and `/readyz`.
- [ ] No production secrets/data are used in test.
- [ ] All remaining zero-replica workloads are classified individually; stateful, scheduled, worker, and cluster-dependent workloads are not bulk-enabled.
- [ ] Durable runtime, persistent data, DNS/ingress, TLS, observability, and rollback are proven before production cutover.
- [ ] Public website/API smoke tests pass after an explicitly reviewed cutover.

Until all applicable gates pass, status remains **BLOCKED for production migration**.
