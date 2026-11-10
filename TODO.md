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

## Full-functional frontend repair

- [ ] Ensure production browser API requests target the unified API origin and retry token refresh correctly.
  - Browser business mutations use `https://api.shopnoltd.dpdns.org`; internal service hosts are never required by the browser.
  - Storage mutations use the same unified API facade.
- [ ] Make public blog loading expose a usable loading, empty, retry, and service-unavailable state.
  - Published articles must render when the blog service is healthy.
  - The page must not claim success when the backend returns an error.
- [ ] Make domain availability and registration use the unified API with authenticated registration and idempotency.
  - Availability must return a real available/taken result or an explicit service-unavailable error.
  - Registration must not fabricate an order or payment result.
- [ ] Provide a usable contact path with validation and an honest confirmation/error state.
- [ ] Preserve login, checkout, protected routes, direct refresh, mobile navigation, and SEO route output.
- [ ] Validate the repair with build, browser contract, Python compilation, and Kubernetes render checks.
- [ ] Keep production merge/deployment as an explicit follow-up after review and live runtime verification.
