# Shopno Ltd (shopnoltd)

Multi-tenant platform: domain/subdomain registration with auto-provisioned
per-user services, an admin control plane, and user-facing site management
(theme/code/publish), payments, and storage — built as independent FastAPI
services behind a gateway, with React admin/web portals.

This README reflects what is **actually implemented** in this repo today,
not the eventual full vision. Update it as real features land.

## What's real right now

| Service | Path | Status |
|---|---|---|
| Gateway | `platform/gateway` | Basic routing + Keycloak-based auth check |
| Auth service | `platform/auth-service` | Session + auth API |
| OAuth service | `platform/oauth-service` | Node/Express OAuth routes |
| Domain service | `platform/domain-service` | Zones/records/registrars API, PowerDNS client |
| Payment service | `platform/payment-service` | Wallets, transactions, exchange rates; provider stubs for Stripe / bKash / crypto / Binance Pay / manual |
| Storage service | `platform/storage-service` | Buckets/objects API over MinIO (S3-compatible) |
| Admin portal | `platform/admin-portal` | React app — Users, Tenants, Payments, Plans, Streams, App Releases, **3D Dashboard** |
| Web portal | `platform/web-portal` | React app — Register, Login, Dashboard, Pricing, Blog, Plugins |

Roughly 25 other directories under `platform/` (analytics, mail, meet,
messaging, notification, license, audit, etc.) currently contain **only a
Dockerfile and the same generic FastAPI boilerplate** — they are placeholders,
not working services yet. Treat anything not in the table above as "not built."

Two top-level directories (`api-service`, `tenant-router`) are also stubs
(Dockerfile only, no app code).

## Known gaps (fix before deploying anywhere real)

1. **No license.** `LICENSE` was empty — this repo currently has no stated
   usage terms. A placeholder "all rights reserved" notice is included; get
   an actual license decision (proprietary vs. open-core, etc.) from whoever
   owns the business before this goes anywhere public.
2. **`docker-compose.yml` was empty.** The one in this fix wires up the
   services that have real code (see table above) plus Postgres/Redis/MinIO.
3. **Auth depends on Keycloak, which isn't provisioned anywhere in this repo.**
   `auth-service`, `oauth-service`, and `gateway` all reference a Keycloak
   issuer URL. You need to stand one up (or swap the auth approach) before
   login actually works end-to-end.
4. **`domain-service` depends on PowerDNS**, also not included yet.
5. **Config defaults point at Kubernetes-internal DNS** (e.g.
   `postgres.data.svc.cluster.local`), which won't resolve locally — use the
   `.env` overrides in `.env.example`.
6. **A copy of a third-party APK (`APKPure_3.20.7402_apkpure.com.apk`) is
   committed at repo root.** That's someone else's proprietary software —
   remove it. Redistributing it (rebranded or not) isn't something to build
   on top of.
7. **KoboToolbox branding overlay** (`branding/`) appears to be legitimate
   white-labeling of the open-source KoboToolbox/KoBoCollect stack — keep the
   required upstream license/attribution notices intact when you ship this.

## Running locally

```bash
cp .env.example .env
# edit .env with real values (see comments in the file)
docker compose up --build
```

This starts: Postgres, Redis, MinIO, gateway, auth-service, oauth-service,
domain-service, payment-service, storage-service, admin-portal, web-portal.

It will **not** fully function end-to-end yet because of gaps #3 and #4
above — you'll be able to hit each service's `/healthz` and its own API
routes, but login and domain provisioning need Keycloak/PowerDNS wired in.

## Suggested next steps, in order

1. Stand up Keycloak + PowerDNS locally (or swap auth/DNS approach) so
   auth-service and domain-service actually work end-to-end.
2. Build the real registration → auto-provision flow: web-portal `Register`
   → auth-service creates account → domain-service registers
   subdomain → a new tenant instance gets provisioned.
3. Flesh out admin-portal's `Tenants`/`Users` pages to actually call the real
   APIs (verify what's wired vs. still using mock data).
4. Decide license/ownership, replace the placeholder LICENSE.
5. Remove the committed third-party APK.
