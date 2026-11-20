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

export DATABASE_URL=postgresql://<user>:<password>@localhost:5432/session_manager
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
3. The existing `.github/workflows/build-platform.yml` already builds this service when `platform/session-manager/**` changes.
4. Create the secret (real values, run from WSL2):
   ```bash
   kubectl create namespace shopno-tools --dry-run=client -o yaml | kubectl apply -f -
   kubectl label namespace shopno-tools name=shopno-tools --overwrite

   kubectl -n shopno-tools create secret generic session-manager-secrets \
     --from-literal=DATABASE_URL="postgresql://<user>:<password>@<postgres-host>:5432/session_manager" \
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

## API authentication and ownership

All `/api/profiles/*` and `/api/sessions/*` endpoints require a Keycloak RS256 access token in `Authorization: Bearer <token>`. Tokens are checked against the Shopnoltd realm issuer, `api-service` audience, expiry, and realm JWKS. The owner is taken only from the verified token `sub`; a request body cannot choose or override it.

- `POST /api/profiles` — create a profile (`purpose`: `qa`, `staff`, or `scraping`).
- `GET /api/profiles` — list only the caller's profiles.
- `GET/DELETE /api/profiles/{profile_id}` — read/delete only an owned profile.
- `POST /api/sessions/launch` — launch a session for an owned profile.
- `POST /api/sessions/{profile_id}/viewer-ticket` — issue a one-time, short-lived viewer URL for an active owned session.
- `GET/POST /api/sessions/{profile_id}/tabs` — list or open a tab in an owned active browser.
- `POST /api/sessions/{profile_id}/tabs/{tab_id}/navigate` and `/focus`, `DELETE .../{tab_id}` — navigate, focus, or close an owned tab.
- `GET /api/sessions/{profile_id}/downloads` and `GET .../downloads/{download_id}` — list and retrieve only the caller's browser downloads; files are stored under that profile's managed data directory and removed with the profile.
- `POST /api/sessions/{profile_id}/close` and `GET /api/sessions/active` — operate on/list only the caller's sessions.
- `POST /api/agent/profiles/{profile_id}/tabs/{tab_id}/actions` — authenticated Agent bridge into the same owner-scoped Playwright tab. The Agent token is revalidated on every action; only the Agent Service pods may reach this route through the in-cluster NetworkPolicy. File uploads are capped at 4 MiB and keyboard keys are allow-listed. A browser click, form submit, or file selection is reported as dispatched/selected, not as proof that the destination website accepted it.
- Proxy CRUD and profile proxy assignment are disabled until proxy records have equivalent tenant ownership.

## Live session viewing

The Kubernetes noVNC ingress and Service port remain removed. Live viewing is provided through the authenticated viewer gateway: an owner-scoped API call issues a 60-second single-use ticket, the bootstrap exchanges it in a same-origin POST, and an HttpOnly/Secure/SameSite cookie is scoped to that profile's WebSocket path for 10 minutes. The gateway checks the verified owner, profile, active session, and allowed Origin before proxying to loopback `127.0.0.1:6080`. Browser navigation and subresource requests are blocked when they resolve to private, loopback, link-local, or cluster-local addresses. The Kubernetes egress policy permits DNS, the Session Manager PostgreSQL pod, and public HTTP(S) only; the noVNC port is never exposed as a Service or Ingress. Do not expose port 6080 directly. Browser processes remain single-replica and in-memory; do not scale the deployment horizontally without a shared session broker.

## Migration and rollout gates

- Existing profiles may have legacy username/email values in `owner`. They are not automatically converted to Keycloak `sub`; prepare and review an identity mapping before migrating them. No database migration is performed by this change.
- Verify the Keycloak `api-service` audience mapper for tokens issued to the Shopnoltd web client.
- Confirm the running Session Manager image includes the authenticated viewer gateway and that GitOps keeps the `session-manager-vnc` Ingress absent before enabling the viewer.
- Do not restart or roll out production until the PR checks pass and a capacity/rollback review is recorded.
