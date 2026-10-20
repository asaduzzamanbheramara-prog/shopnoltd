# Codespaces zero-replica service preflight

Status: **preflight only — not a production migration or deployment**.

## Goal

Use GitHub-hosted CI to establish whether the three Python services below can be built from the repository while leaving the currently declared production replica count unchanged:

- `interior-service`
- `license-service`
- `training-service`

The workflow `.github/workflows/codespaces-zero-replica-preflight.yml` verifies each service's source files and its reviewed replica-count invariant before building the image without publishing it. The expected source-manifest values are `interior-service: 1`, `license-service: 0`, and `training-service: 0`. It then starts each image against disposable PostgreSQL and Redis service containers and checks `/healthz` and `/readyz`. These are repository expectations, not claims about live cluster state.

## What a PASS proves

- The selected Docker build completes from the checked-out commit.
- Required source files exist.
- Each source manifest declares its reviewed expected replica count at the tested commit (`interior-service: 1`; `license-service` and `training-service: 0`).
- The image starts in an isolated GitHub Actions runner with disposable PostgreSQL and Redis and passes `/healthz` and `/readyz`.

## What a PASS does not prove

- The live cluster matches the repository manifest, or that any service has been migrated to Codespaces.
- Production PostgreSQL, Redis, PVCs, secrets, queues, ingress, or provider dependencies are available. The smoke test uses only disposable PostgreSQL/Redis and test-only credentials.
- A service has been deployed to a Codespace, or that it can remain running when the Codespace stops.
- Production traffic has moved away from the PC-hosted K3s cluster.

Each service's application startup calls dependency checks for PostgreSQL and Redis and runs SQLAlchemy metadata creation. The workflow provides disposable PostgreSQL and Redis, test-only credentials, and cleanup. A successful smoke test is only a container-level check, not a production deployment.

## Safety and rollout rules

1. Keep the production K3s cluster and public routing unchanged until migration acceptance and rollback checks pass.
2. Never commit or copy production kubeconfig, Kubernetes Secret values, database passwords, Cloudflare credentials, or production user data into Codespaces, Actions logs, artifacts, or this repository.
3. This workflow must not change production replica counts. It has no Kubernetes credentials and no deployment/publish step; the per-service expected counts are guardrails, not scale commands.
4. Before moving any workload, inventory its live effective replica count, PVC/data dependencies, service-to-service dependencies, required environment variable **names** (not values), resource needs, ingress, restart behavior, and rollback.
5. GitHub Actions runners are ephemeral and Codespaces can stop when idle. Neither is a durable always-on production runtime. GHCR distributes images; it does not run them.
6. To meet the requirement that production continues while the PC/server is passive, select and validate a durable runtime with persistent storage and networking, then migrate one service at a time. Do not represent this preflight as completion of that migration.

## Acceptance gates

- [ ] Workflow passes for all three service builds.
- [ ] The workflow's isolated PostgreSQL + Redis runtime smoke test passes for all three services.
- [ ] No production secrets/data are used in test.
- [ ] All remaining zero-replica workloads are classified individually; stateful, scheduled, worker, and cluster-dependent workloads are not bulk-enabled.
- [ ] Durable runtime, persistent data, DNS/ingress, TLS, observability, and rollback are proven before production cutover.
- [ ] Public website/API smoke tests pass after an explicitly reviewed cutover.

Until all applicable gates pass, status remains **BLOCKED for production migration**.
