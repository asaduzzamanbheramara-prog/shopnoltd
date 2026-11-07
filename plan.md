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
