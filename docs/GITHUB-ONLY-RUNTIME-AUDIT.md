# GitHub-only runtime audit and safe migration plan

**Audit date:** 2026-10-20  
**Scope:** GitHub-only source, build, artifact, and automation options. No production resources were changed by this audit.  
**Status:** Repository and prior read-only inventory reviewed; production migration is **BLOCKED** until a GitHub-compatible persistent runtime and data plan exist.

## Executive decision

Shopnoltd can use GitHub as its source of truth for code, Kubernetes manifests, GitOps review, CI, image builds, GHCR artifacts, and deployment automation. GitHub Codespaces and GitHub Actions jobs are not a replacement for an always-on production Kubernetes runtime. Therefore, with the constraint “no external cloud provider,” the repository can be made more reproducible and safer, but this audit cannot honestly mark a full 24/7 production migration as complete.

GitHub Pages can host a static site. It cannot run the existing multi-service backend, PostgreSQL, Keycloak, object storage, queues, workers, or Kubernetes control plane. Repointing the current production domain to a static build would remove dynamic functionality and is not proposed.

## Verified baseline

The latest supplied read-only live inventory artifact was produced by GitHub Actions run [39441974185](https://github.com/asaduzzamanbheramara-prog/shopnoltd/actions/runs/39441974185), artifact [12273663842](https://github.com/asaduzzamanbheramara-prog/shopnoltd/actions/runs/39441974185/artifacts/12273663842), at 2026-10-20T14:55:23Z, revision `b79dadc60aaa05c2bf8f6f4bb75ed8eeee7c730b`.

- K3s node: `shopnoltd-pc-1`, Ubuntu under WSL2, internal IP `192.168.0.102`; this means the live cluster depends on the PC/WSL2 host being powered and connected.
- Root Argo CD application: `shopnoltd`, Synced/Healthy at the inventory revision.
- Node utilization in that snapshot: CPU 2188m / 27%; memory 10585Mi / 88%. Starting every zero-replica workload at once would be unsafe without capacity measurements.
- Core app, database, identity, cache, object storage and tunnel workloads were mostly running at that snapshot. Their continued operation does not mean they have been migrated away from the node.
- The zero-replica inventory included app services/workers (`code-server`, `gitea`, Kobo worker/beat, `ollama`, `owncast`), monitoring (`grafana`, `loki`, `prometheus`), platform services (`android-cloud-controller`, `license-service`, `training-service`), and six `default`-namespace Argo CD lookalike deployments.
- The `default` namespace Argo CD lookalikes should not be scaled up blindly: the actual Argo CD installation was in namespace `argocd` and reported running.
- GitOps source `k8s/kustomization.yaml` includes PostgreSQL, Redis, MinIO, MongoDB, Keycloak, cloudflared and many application services. PostgreSQL is configured with a PVC (`postgres-data`) and a single-replica Recreate Deployment. The cloudflared Deployment uses a runtime Kubernetes Secret (`cloudflared-creds`).
- The read-only inventory workflow uses `runs-on: [self-hosted, linux]`. This is a dependency on an online self-hosted runner for that workflow; it is not GitHub-hosted compute. Prior troubleshooting also showed the runner was on the local PC/WSL environment.

## What GitHub can and cannot provide

| Capability | GitHub-only status | Safe interpretation |
|---|---|---|
| Source control, review, issue tracking | Supported | Keep `main` as source of truth; changes reviewed through PRs. |
| CI/build/test jobs | Supported with GitHub Actions, subject to plan and usage limits | Jobs are bounded execution, not persistent daemons. Prefer GitHub-hosted runners for jobs that do not need the private live cluster. |
| Container image storage | GHCR supports publishing and pulling images | Store immutable, commit-tagged images; image storage does not run containers. |
| GitOps manifests / Argo CD config | Supported as repository content | GitHub stores desired state; an online Kubernetes cluster is still required to reconcile it. |
| Codespaces | Development environment only for this purpose | Running processes stop when a Codespace stops/times out; documented maximum lifetime is 12 hours. Do not use it as the 24/7 production host. |
| GitHub Pages | Static website hosting | May host a static informational/frontend build if separately validated; it cannot replace Shopnoltd's backend/data services. No DNS change is proposed. |
| Persistent production API, database, queues, identity, object storage, Kubernetes | **Not provided by GitHub repository/Actions/Codespaces alone** | With the no-external-provider constraint, 24/7 migration is blocked unless an already-owned, independent always-on runtime is identified and accepted. |

Official references:
- [Codespaces lifecycle](https://docs.github.com/en/codespaces/about-codespaces/understanding-the-codespace-lifecycle) — inactivity timeout and 12-hour maximum lifetime.
- [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) — static site hosting.
- [GitHub Actions limits](https://docs.github.com/en/actions/reference/limits) — workflow execution and service limits.

## Safe next steps

### Phase 1 — GitHub-first release pipeline
1. Keep the current live cluster untouched while the target is unresolved.
2. Make CI jobs that only lint/render/test manifests use GitHub-hosted runners where possible.
3. Keep cluster-mutating jobs explicitly separated, least-privileged, manually gated, and disabled unless a valid target context is available.
4. Build/publish commit-addressed GHCR images and deploy by immutable digest or commit tag, not floating `latest` tags where feasible.
5. Publish sanitized deployment/inventory evidence as short-retention Actions artifacts; never upload Secret values, kubeconfigs, database dumps, or credentials.

### Phase 2 — classify each zero-replica workload
For each zero-replica object, record owner, user-facing dependency, memory/CPU request, PVC/data needs, ingress/service references, secrets, and a rollback. Do not treat every zero replica as a defect. In particular, inspect duplicate `default` namespace Argo CD objects separately from the active `argocd` namespace.

### Phase 3 — data and runtime prerequisites
Before any move, inventory and validate:
- PostgreSQL databases and a restorable encrypted backup; test restore into an isolated target.
- Keycloak realm/configuration and its database relationship.
- MinIO objects, MongoDB/Redis persistence requirements, all PVCs and local-path assumptions.
- Kubernetes Secrets/configuration by names and references only; recreate secret material through secure configuration, never commit it.
- DNS/Cloudflare tunnel origin routing, TLS, ingress, health/readiness checks, and rollback.
- Required persistent CPU/memory/disk capacity and external connectivity.

### Phase 4 — cutover gate
A cutover is allowed only after the target is known to be independent of the local PC, data restore is proven, all critical service smoke tests pass, observability is available, and rollback is rehearsed. No traffic/DNS changes, PVC replacement, database migration, or blanket replica changes are authorized by this document.

## Acceptance criteria

- [ ] The chosen production runtime is explicitly identified and is allowed by the user's GitHub-only constraint.
- [ ] Runtime is independent of the local PC/WSL2 and has an honest 24/7 availability model.
- [ ] Data backup and isolated restore are tested.
- [ ] Required secrets are provisioned securely and never printed or committed.
- [ ] Each zero-replica deployment has a documented reason and owner; stale duplicates are not revived.
- [ ] All required services pass health/readiness, auth, API, and browser smoke tests.
- [ ] DNS/ingress cutover and rollback are tested.
- [ ] The public site and critical API are verified after cutover.

**Current result:** Audit = PASS for documenting the architecture and constraints. Full GitHub-only 24/7 production migration = **BLOCKED** by the lack of a persistent runtime in GitHub-only services. No production workloads, storage, databases, or DNS were changed.
