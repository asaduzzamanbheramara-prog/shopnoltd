# Unified browser-first Shopnoltd app

## Goal

Provide an authenticated `/app` workspace that behaves like a browser-installable Manus-style shell for Shopnoltd AI and code-server, while preserving the existing AI and shared code-server services. Deploy one isolated code-server workspace through the existing GitHub-to-Argo CD pipeline.

## Implementation

- Add a protected `/app` route with a responsive workspace shell, AI and Code launch cards, runtime health indicators, and PWA-friendly navigation.
- Point the AI and Code Server catalog entries to the unified app shell while retaining direct routes for backward compatibility.
- Add a dedicated `code-server-isolated` Kubernetes workload with its own PVC, Service, ConfigMap, Deployment, and Ingress hostname. Reuse only existing runtime secret names; do not commit values.
- Add browser-extension launch actions for the app shell, AI, and isolated code workspace. Keep token handling unchanged and never persist new secrets.
- Extend the route metadata and app manifest start URL to make `/app` the browser-first workspace entry while keeping `/` as the public landing page.

## Runtime boundaries

GitHub remains the source of truth. Argo CD syncs the manifests from `main`. Database credentials, AI provider keys, code-server keys, and deployment credentials stay in the PC/server or cluster secret store. The new workspace is intentionally a single replica with a dedicated `ReadWriteOnce` PVC and a separate hostname.

## Validation

Run the web build, Kustomize render, YAML validation, extension syntax checks, and public health checks. Do not report the isolated workspace as live until Argo CD syncs it and the new hostname returns a healthy code-server session.

## Live frontend repair — 2026-11-11

### Goal
Restore a single, browser-first frontend contract for `https://shopnoltd.dpdns.org` and make the public blog, domain search/registration, contact, authentication, checkout, and protected service routes use the unified API origin consistently.

### Implementation
- Make all browser API and storage mutations resolve through `https://api.shopnoltd.dpdns.org` in production, while preserving Vite overrides for other environments.
- Preserve real service behavior: surface backend unavailability honestly, never fabricate registrations, payments, blog writes, or support tickets.
- Add a functional contact request flow only when a server endpoint exists; otherwise keep a direct support email fallback with clear user guidance.
- Add public route and smoke coverage for the observed blog/domain failures and deep-link behavior.
- Verify the portal build, Python compilation, Kubernetes rendering, and focused browser/service contract checks.

### Runtime boundary
Code changes can be prepared and pushed to a repair branch. Production merge, Argo CD reconciliation, and live payment/domain/provider operations remain separate deployment steps and require runtime credentials/cluster access that are not present in this sandbox.
