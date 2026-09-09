# Shopnoltd self-hosted k3s GitHub Actions runner

This runner is the trusted bridge between GitHub Actions and the private Shopnoltd k3s cluster. It is intentionally used only by workflows that run from trusted `main` source; pull requests are never scheduled on this runner.

## One-time setup

1. On the Shopnoltd k3s node, create/use a dedicated non-root runner account.
2. Ensure that account has a working `kubectl` and a kubeconfig with only the Kubernetes permissions required by `.github/workflows/self-hosted-k3s-gitops.yml`.
3. In GitHub repository settings, create a short-lived self-hosted-runner registration token.
4. On the runner node, export the token only in the shell environment:

```bash
export RUNNER_TOKEN='REDACTED_SHORT_LIVED_TOKEN'
```

Do **not** put this token in the repository, `.env` files committed to Git, workflow YAML, shell history, or issue comments.

5. Run the bootstrap script from this repository checkout:

```bash
bash ops/github-runner/bootstrap-k3s-runner.sh
```

The script discovers the current GitHub Actions runner release unless `RUNNER_VERSION` is explicitly supplied, configures labels `self-hosted,linux,shopnoltd,k3s`, installs the runner as a service, and starts it.

6. Verify the runner appears online in GitHub repository Settings -> Actions -> Runners.

## Kubernetes access

The deployment workflow needs access to:

- Argo CD `Application` `shopnoltd` in namespace `argocd`: get + patch.
- Migration Job/pods/events in namespace `shopno-data`: get/list/read.
- Cloudflared Deployment/pods/logs in namespace `shopno-ingress`: get/read.
- Cluster discovery required by `kubectl cluster-info`.

Do not give the runner cluster-admin unless an independent security review proves it necessary. Prefer a dedicated kubeconfig/RBAC identity.

The kubeconfig is runtime infrastructure and must never be committed to GitHub.

## Automatic deployment

`.github/workflows/self-hosted-k3s-gitops.yml` runs on pushes to `main` that change Kubernetes source and can also be started manually.

It:

1. checks the runner and Kubernetes access;
2. renders `k8s` with Kustomize;
3. requests an Argo CD hard refresh and syncs the exact GitHub commit;
4. waits for `shopnoltd` to become `Synced` and `Healthy`;
5. verifies the live Cloudflared image exactly matches the GitHub manifest;
6. verifies the PostgreSQL migration hook completed when the hook Job is retained;
7. on failure, emits Argo CD status, migration Job/pod logs and events, and Cloudflared status/logs.

The existing public post-deployment smoke workflow remains the public release check. This runner workflow does not weaken or bypass it.

## Migration-failure diagnostics

The migration is deliberately fail-closed. A failed migration must remain visible as a failed deployment rather than being ignored. The diagnostic step collects the Job description, pod state, container logs, recent namespace events, and Argo CD operation message without printing Kubernetes secrets.

The migration SQL itself remains authoritative in `k8s/services/postgres/migration/`. Do not modify it merely to make the workflow green; fix the underlying schema or dependency problem and verify the resulting migration.

## Security model

- Never execute this workflow from untrusted pull-request code.
- Never store kubeconfig, Cloudflare tunnel credentials, database passwords, or runner registration tokens in Git.
- Keep Cloudflare credentials in the existing external secret/env mechanism.
- Keep deployment and release gates fail-closed.
- Treat a green GitHub workflow as necessary evidence, not permission to skip runtime verification.
