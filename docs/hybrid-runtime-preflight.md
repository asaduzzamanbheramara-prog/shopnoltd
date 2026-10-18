# Shopnoltd hybrid runtime preflight

Status: **planning/preflight only**. This document does not authorize production changes.

## Architecture boundary

- GitHub repository: source of truth for manifests, workflows, and review.
- GitHub Actions on hosted runners: CI/render validation only; runners are ephemeral.
- GHCR: immutable image distribution, not a runtime.
- Existing local K3s node: current production runtime; preserve it until acceptance checks and rollback are proven.
- Codespaces: development and integration testing only. Its current devcontainer starts a Vite preview on port 5173; it is not a durable Kubernetes production replica.
- **Owner's requested split:** keep currently live production services on the PC-hosted K3s cluster; investigate each service at zero replicas as a candidate to run in Codespaces only if it is stateless or has safe external dependencies and can tolerate Codespaces stopping. Do not move live production traffic or claim the zero-replica services are migrated until individually deployed and tested.

## Explicit Codespaces candidate policy

The existing Codespaces configuration installs the web portal dependencies and starts a Vite preview on port 5173. It does not provision Kubernetes, build a service mesh, or start the zero-replica Kubernetes workloads. Codespaces can host temporary development/test processes, but not a guaranteed always-on replica.

- **Reasonable first Codespaces test candidate:** web/UI development preview and isolated stateless services with test-only configuration, after checking each service's build/run instructions and ports. Keep any forwarded ports private unless public access is deliberately required.
- **Not safe to move as-is:** database/storage systems (PostgreSQL, Redis, MinIO, Gitea with data), schedulers/workers (Kobo beat/worker), production n8n/background jobs, monitoring that depends on durable retention, Android Cloud/device controllers, and any service with PVCs, privileged access, cluster-admin credentials, or dependencies reachable only inside K3s. These require redesign, persistent shared services, secure credentials, and explicit testing first.
- **Production availability rule:** if a Codespace stops, all processes in it can stop. Therefore a Codespace-hosted process must not become the only production copy or receive production traffic that cannot safely fail back to the PC. Keep the PC instance and routing unchanged until an independently persistent runtime exists or the owner explicitly accepts the availability limitation.
- **Do not copy production kubeconfig, Kubernetes Secrets, database passwords, Cloudflare credentials, or user data into Codespaces or GitHub files.** Use least-privilege, short-lived credentials and sanitized test data only.
- For every zero-replica entry, record: live namespace/name and actual desired/ready count; manifest source/overlay; reason disabled; data/PVC/queue/scheduler dependencies; Codespaces run method; required environment variables (names only); port and health check; resource use; stop/restart behavior; and rollback. Only then promote an individual candidate.

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

## Gate 1A — Known manifest entries declared at zero replicas

A GitHub code search at repository revision `eca8f614c771eaed8ec8d331d10b276ec0b0e680` found these manifest entries explicitly set to `replicas: 0`. This is a **source-manifest inventory, not a current live-cluster inventory**; overlays, later commits, and live drift may change the effective count. Re-run Gate 0 against the live cluster before acting.

| Workload / manifest | Initial disposition |
| --- | --- |
| Ollama — `k8s/ollama.yaml` | Keep off until GPU/CPU/memory capacity, model storage, and actual product dependency are confirmed. |
| Kobo beat — `k8s/shopno-apps/kobo-beat.yaml` | Scheduler: do not run a duplicate without leader/queue ownership review. |
| Kobo worker — `k8s/shopno-apps/kobo-worker.yaml` | Queue worker: verify broker, queue depth, idempotency and concurrency before enabling. |
| Loki — `k8s/services/loki/deployment.yaml`; monitoring Loki — `k8s/services/observability/loki-deployment.yaml` | Observability workload; verify storage and current logging stack before enabling. |
| Gitea — `k8s/services/gitea/deployment.yaml` | Stateful Git service; verify PVC and whether it is intentionally retired before enabling. |
| Owncast — `k8s/services/owncast/deployment.yaml` | Optional streaming workload; enable only if explicitly required and capacity is available. |
| OnlyOffice — `k8s/services/onlyoffice/deployment.yaml` | Optional document service; check CPU/memory and document-storage integration first. |
| Code-server — `k8s/services/code-server/deployment.yaml` | Interactive development service; do not treat it as the GitHub Codespaces runtime or enable it by default. |
| Alertmanager — `k8s/services/alertmanager/deployment.yaml`; Grafana — `k8s/services/observability/grafana-deployment.yaml`; Prometheus — `k8s/services/observability/prometheus-deployment.yaml` | Monitoring stack; verify the intended replacement/retention and persistent storage before enabling. |
| Android Cloud controller — `k8s/services/android-cloud/deployment.yaml` | Controller may cause workload/resource changes; require explicit feature and resource review. |
| License service — `k8s/services/license-service/deployment.yaml` | Check feature dependency and licensing behavior before enabling. |
| Interior service — `k8s/services/interior-service/deployment.yaml` | Check product dependency, configuration and resources before enabling. |
| Training service — `k8s/services/training-service/deployment.yaml` | Check product dependency, configuration and resources before enabling. |

Do **not** bulk-scale these workloads up, copy them into Codespaces, or alter GitOps manifests just because their replica count is zero. Some are stateful, background schedulers, optional features, or potentially intentionally disabled. First match the live namespace/name and owner to the source manifest and establish why it is off.

## Gate 1B — Duplicate Argo CD in `default`

The previously verified operational action was to scale the seven duplicate Argo CD workloads in namespace `default` to zero while preserving all objects. The canonical controller remains `argocd/shopnoltd` in namespace `argocd`. Keep the duplicate down and retain its resources until ownership/dependency review is complete; do not delete the namespace or its data as part of migration.

The seven duplicate workloads are:
- Deployments: `argocd-applicationset-controller`, `argocd-dex-server`, `argocd-notifications-controller`, `argocd-redis`, `argocd-repo-server`, `argocd-server`
- StatefulSet: `argocd-application-controller`

Confirm current desired/ready replicas using Gate 0; this historical record does not guarantee live state now.

## Gate 2 — Choose a real second runtime

A production second runtime must be persistent, independently reachable, patched, monitored, and capable of securely reaching the required shared services. Codespaces and hosted Actions runners do not satisfy this requirement by themselves.

GitHub's documented Codespaces lifecycle includes idle stopping and a maximum lifetime (currently documented as 12 hours). Codespaces should therefore be used for development, validation, and controlled operator tasks—not as an always-on production replica. See [GitHub's Codespaces lifecycle documentation](https://docs.github.com/en/codespaces/about-codespaces/understanding-the-codespace-lifecycle).

If no second always-on runtime is available, mark high availability **BLOCKED**. Keep the existing public route unchanged.

## Gate 3 — Shared state and secure connectivity

Before traffic can reach two runtimes, document:
- database ownership, migrations, backup/restore, and network access;
- session/authentication consistency and key rotation;
- object/file storage consistency;
- secrets delivery without committing secrets;
- internal service discovery, TLS, firewall policy, and health-check behavior;
- background-job ownership to prevent duplicate execution.

Do not expose database/admin ports publicly as a shortcut. Never copy the production kubeconfig or secret material into Codespaces.

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
