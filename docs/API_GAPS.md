# Known API Gaps (admin-portal)

Found while fixing `nginx.conf`'s missing `/api` proxy (same class of bug as
web-portal had). These are honest gaps, not wired to fake data:

- **`Plans.jsx` (`/api/plans`) and `AppReleases.jsx` (`/api/releases`)** --
  no backend implements either route anywhere in the repo. These pages will
  502 until something exposes them (billing-engine for plans; a
  release-tracking table/endpoint for app releases -- doesn't exist yet).
- **`Streams.jsx` (`/api/streams`)** -- the backend code exists
  (`platform/live-service`), but it was never migrated to
  `k8s/services/live-service/` -- only old files under `k8s/legacy/` reference
  it. Give it a proper `k8s/services/live-service/` directory (copy the
  pattern from any other service) before this will resolve to anything.

Proxy routing for everything else that IS wired is in `nginx.conf`, one
`location` block per backend service.
