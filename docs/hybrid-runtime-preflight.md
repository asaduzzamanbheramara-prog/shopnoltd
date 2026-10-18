# Shopnoltd hybrid runtime preflight

Status: **planning/preflight only**. This document does not authorize production changes.

## Architecture boundary

- GitHub repository: source of truth for manifests, workflows, and review.
- GitHub Actions on hosted runners: CI/render validation only; runners are ephemeral.
- GHCR: immutable image distribution, not a runtime.
- Existing local K3s node: current production runtime; preserve it until acceptance checks and rollback are proven.
- Codespaces: development and integration testing only. Its current devcontainer starts a Vite preview on port 5173; it is not a durable Kubernetes production replica.

## Gate 0 — Read-only production inventory

Run from the authorized machine that has the existing K3s kubeconfig. Never copy the production kubeconfig or secrets into Codespaces or repository files.

```bash
set -eu
kubectl config current-context
kubectl get nodes -o wide
kubectl get applications.argoproj.io -n argocd shopnoltd -o wide
kubectl get deployments -A -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,DESIRED:.spec.replicas,READY:.status.readyReplicas,AVAILABLE:.status.availableReplicas'
kubectl get statefulsets -A -o wide
kubectl get daemonsets -A -o wide
kubectl get pvc -A -o wide
kubectl get ingress -A -o wide
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded -o wide
kubectl top nodes
kubectl top pods -A
```

Record output securely; do not paste secret values or full Secret YAML into issues/logs.

## Gate 1 — Classify workloads

Before changing replicas, review each candidate Deployment's manifest and dependencies:
- **Potential horizontal candidates:** stateless HTTP services only after verifying externalized sessions, shared database/storage, idempotent startup, readiness/liveness probes, and resource headroom.
- **Do not scale by default:** PostgreSQL, Redis, MongoDB, MinIO, queues, schedulers, migration hooks, n8n workers/schedulers, Kobo beat/worker, Ollama, code-server, Android Cloud controller, or anything with local/PVC state. First verify clustering, leader election, queue semantics, licensing, storage access mode, and resource demand.
- Do not assume a workload at zero replicas is safe to enable. Determine why it was disabled and validate dependencies and capacity first.

## Gate 2 — Choose a real second runtime

A production second runtime must be persistent, independently reachable, patched, monitored, and capable of securely reaching the required shared services. Codespaces and hosted Actions runners do not satisfy this requirement by themselves.

If no second always-on runtime is available, mark high availability **BLOCKED**. Keep the existing public route unchanged.

## Gate 3 — Shared state and secure connectivity

Before traffic can reach two runtimes, document:
- database ownership, migrations, backup/restore, and network access;
- session/authentication consistency and key rotation;
- object/file storage consistency;
- secrets delivery without committing secrets;
- internal service discovery, TLS, firewall policy, and health-check behavior;
- background-job ownership to prevent duplicate execution.

Do not expose database/admin ports publicly as a shortcut.

## Gate 4 — Acceptance and controlled rollout

Required before changing DNS/tunnel/routing:
1. Render manifests and run CI checks.
2. Confirm both runtimes run the same immutable image digest and compatible configuration.
3. Verify public homepage, API `/healthz` and `/readyz`, OIDC discovery/login, admin authorization, and browser journeys.
4. Verify database read/write, object storage, mail, and queued/background work.
5. Restart one candidate instance and prove service remains healthy.
6. Test loss of the second runtime and recovery; inspect resource pressure and error rates.
7. Shift a small amount of traffic, monitor, and document rollback to the existing route.
8. Keep the original runtime and rollback path until an agreed observation window passes.

## Rollback

Restore the last known-good routing/tunnel configuration and immutable image digest. Do not scale down or remove the original K3s runtime as part of initial rollout. Stop rollout immediately on failed readiness, authentication, data consistency, elevated errors, or resource pressure.

## Evidence reporting

Report each gate as **PASS**, **BLOCKED**, or **FAIL**, with timestamp, commit/image digest, and sanitized command output. A GitHub workflow passing a manifest render is not proof that production is healthy.
