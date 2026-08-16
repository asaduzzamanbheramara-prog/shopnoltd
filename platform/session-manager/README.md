# Shopnoltd Session Manager

Isolated browser-session management for:
- QA testing your own Shopnoltd services under different test accounts
- Staff tooling — each team member gets an isolated authenticated session
- Web scraping at scale with per-worker session/proxy isolation

Each **profile** gets its own persistent Playwright browser context (own
cookies, localStorage, cache). This is standard multi-tenant session
isolation — it does **not** do fingerprint randomization or anti-detection
spoofing, so it isn't suited to platform ad-account evasion, and that's
intentional.

## Local dev

```bash
cd platform/session-manager
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium --with-deps

export DATABASE_URL=postgresql://postgres:5XuByzqhn6nJyq7iR7xva58iKHLSUSj@localhost:5432/session_manager
export SESSION_MANAGER_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

python3 -c "from app.models.db import init_db; init_db()"
uvicorn app.main:app --reload
```

Open http://localhost:8000

## Deploying into the shopnoltd monorepo

1. Copy this whole folder to `platform/session-manager/` in your monorepo.
2. Copy your existing branding assets in:
   ```bash
   cp -r branding/* platform/session-manager/branding/
   ```
3. Add a matrix entry for it in `.github/workflows/build-platform.yml` so CI
   builds and pushes `ghcr.io/asaduzzamanbheramara-prog/shopnoltd/session-manager:latest`.
4. Create the secret (real values, run from WSL2):
   ```bash
   kubectl create namespace shopno-tools --dry-run=client -o yaml | kubectl apply -f -
   kubectl label namespace shopno-tools name=shopno-tools --overwrite

   kubectl -n shopno-tools create secret generic session-manager-secrets \
     --from-literal=DATABASE_URL="postgresql://postgres:5XuByzqhn6nJyq7iR7xva58iKHLSUSj@<postgres-host>:5432/session_manager" \
     --from-literal=ENCRYPTION_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
   ```
5. Apply manifests:
   ```bash
   kubectl apply -f platform/session-manager/k8s/deployment.yaml
   ```
6. Push to GitHub, let `build-platform.yml` build the image, then:
   ```bash
   kubectl -n shopno-tools rollout restart deployment/session-manager
   ```

## API surface

- `POST /api/profiles` — create a named profile (`purpose`: qa | staff | scraping)
- `GET /api/profiles` — list profiles
- `POST /api/proxies` — register a proxy (credentials encrypted at rest with Fernet)
- `POST /api/sessions/launch` — launch an isolated session for a profile against a target URL

## Live session viewing (noVNC)

Sessions now run persistently, non-headless, on a virtual display (`Xvfb :99`)
inside the container. `x11vnc` exposes that display over VNC, and
`websockify`/noVNC bridge it to a browser-viewable page at `/vnc.html` on
port 6080.

- **Local (docker-compose):** open http://localhost:8000, create a profile,
  click Launch — it opens a viewer at http://localhost:6080/vnc.html.
- **k8s:** routed through a second Ingress (`session-manager-vnc`) at
  `https://sessions.shopnoltd.dpdns.org/vnc/vnc.html`, since the noVNC
  static assets need a path rewrite that would otherwise conflict with the
  main API ingress.

Sessions stay open until you hit **Close** (or the container restarts) —
this is a single in-memory pool per pod, matching this cluster's
single-replica pattern for stateful services.

## Notes / next steps

- Single-process session pool: fine at `replicas: 1` (which the manifest
  already pins per this cluster's conventions). If this ever needs to scale
  beyond one pod, sessions would need sticky routing or a shared registry —
  not needed yet.
- Wire `owner` on profiles to your Keycloak `auth-service-admin` client so
  staff sessions map to real identities instead of free-text strings.
- **Before exposing `sessions.shopnoltd.dpdns.org` externally**, put this
  behind Keycloak auth on the ingress (e.g. `oauth2-proxy` or ingress-level
  auth annotations) — it's currently unauthenticated and can drive live
  browser sessions holding saved credentials/cookies.
- `x11vnc` currently runs with `-nopw` (no password) for simplicity inside
  the pod network — acceptable since it's only reachable via the
  NetworkPolicy-gated Service, but tighten this if that assumption changes.
