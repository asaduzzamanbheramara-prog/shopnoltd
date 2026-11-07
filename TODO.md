# Implementation outcomes

## Unified browser-first app shell

- [x] Add a protected `/app` route that presents Shopnoltd AI and the isolated Code Server as first-class workspace tools.
- [x] Keep existing `/ai` and shared code-server URLs functional for backward compatibility.
- [x] Show the selected isolated workspace identity and live health state without exposing credentials.

## Single isolated code-server deployment

- [x] Add one dedicated code-server Deployment, Service, ConfigMap, PVC, and Ingress hostname under `k8s/services/code-server-isolated`.
- [x] Use a separate `ReadWriteOnce` PVC and one replica; do not reuse the existing shared workspace PVC.
- [x] Reuse only existing secret names and keep all secret values outside Git.

## Browser extension launch surface

- [x] Add popup actions that open `/app`, `/ai`, and the isolated code-server URL.
- [x] Do not add new token persistence or secret transmission behavior.

## Release validation

- [x] Build the web portal and validate the new Kubernetes YAML with a local parser.
- [x] Validate extension JavaScript and manifest syntax.
- [ ] Push the feature branch to GitHub for review; production availability depends on Argo CD sync and cluster health.
