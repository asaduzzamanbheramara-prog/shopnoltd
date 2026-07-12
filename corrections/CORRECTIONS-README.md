# Shopnoltd — Correction Package

Generated from a full audit of the uploaded repo (`shopnoltd-source_tar.gz`)
against the live cluster state. Every file here replaces a specific
confirmed bug — nothing is speculative.

## Files in this package → where they go in your repo

| File here | Goes to (repo root unless noted) |
|---|---|
| `.github/workflows/docker-build.yml` | `.github/workflows/docker-build.yml` (**replace**) |
| `.github/workflows/build-all.yml` | `.github/workflows/build-all.yml` (**replace**) |
| `deployment-live.yaml` | `deployment-live.yaml` (**replace**) |
| `deployment-tenant-router-configmap.yaml` | new file, repo root |
| `start-tunnel.ps1` | `C:\Users\asadu\start-tunnel.ps1` (**replace**) |
| `watchdog.ps1` | `C:\Users\asadu\watchdog.ps1` (**replace**) |

## What was actually wrong, in the order we found it

### 1. `docker-build.yml` built 5 services from the wrong source
It built `billing-engine`, `oauth`, `chat`, `live`, and `tenant-router` all
from `shopnoltd-ai-platform/backend/Dockerfile` — which only contains the
FastAPI app with `health`/`auth`/`chat` routers. This would have pushed 5
images that all silently ran the same wrong app under different names,
instead of failing loudly. **Confirmed by direct inspection: only 5
Dockerfiles exist in the entire repo** (root `Dockerfile`, `backend/Dockerfile`,
`shopnoltd-ai-platform/Dockerfile`, `ui/Dockerfile`, `ui/admin/Dockerfile`).
The corrected workflow only builds those 5, under the names your
deployments actually expect:

| Job | Real source | Image name |
|---|---|---|
| frontend | `app_platform/` (root `Dockerfile`) | `shopnoltd-frontend` |
| api-service | `shopnoltd-ai-platform/backend/` | `shopnoltd-api-service` |
| ai | `shopnoltd-ai-platform/` | `shopnoltd-ai` (already working — untouched) |
| freedomain-ui | `ui/` | `shopnoltd-freedomain-ui` |
| freedomain-website | `ui/admin/` | `shopnoltd-freedomain-website` |

### 2. `build-all.yml` was a broken, half-finished template
Its matrix pointed at `apps/api-service`, `apps/oauth`, `apps/tenant-router`,
etc. — **none of these directories exist anywhere in the repo** (confirmed:
`find . -iname apps` returns nothing). The file even contained the comment
*"Replace context below with the REAL source directory"* — a placeholder
that was never finished, but because it triggered on every push, it was
running 10 jobs per push with 9 guaranteed to fail. Disabled here
(`workflow_dispatch` only) rather than deleted, in case it reflects a real
future plan — but recommend deleting it outright once you've confirmed
`docker-build.yml` covers what you need.

### 3. `tenant-router-config` ConfigMap didn't exist
We created it directly on the cluster with `kubectl create configmap
--from-file`, which fixed the immediate problem but wasn't reproducible —
your `configmaps.yaml` export still has no such entry. This package adds
`deployment-tenant-router-configmap.yaml` as a real, declarative manifest
built from your actual `tenant-router-nginx.conf`, so a cluster rebuild
won't lose this again.

### 4. `deployment-live.yaml` had `imagePullPolicy: Never`
This tells Kubernetes to *only* look for the image locally and never
contact GHCR — meaning even once an image exists, this pod would never
pull it. Fixed to `IfNotPresent`. **Note: `live` still has no source code
anywhere in the repo** — this fix alone won't make the pod healthy, it'll
just change the error from `ErrImageNeverPull` to `ImagePullBackOff` until
real code exists.

### 5. `start-tunnel.ps1` / `watchdog.ps1` pointed at the wrong port entirely
This is the actual reason the public site kept going down throughout this
whole debugging session, independent of any pod health:
- `cloudflared`'s `config.yml` sends **every** hostname to `127.0.0.1:8080`
- but `start-tunnel.ps1` only ever forwarded **`127.0.0.1:8090`**, pointed
  at `ingress-nginx-controller` — a namespace that **no longer exists**
- `watchdog.ps1` only monitored `8090` and `8091` — **never `8080`**

So nothing was ever automatically keeping port 8080 alive. Every manual
`kubectl port-forward ... 8080:80` we ran together worked only until that
terminal session ended. Both scripts now forward/monitor `tenant-router`
(the real current router) on port `8080`, matching what Cloudflare
actually expects.

## Deploy steps, in order

```bash
# 1. Replace the workflow files, commit, push
cp docker-build.yml build-all.yml  <your-repo>/.github/workflows/
cd <your-repo>
git add .github/workflows/docker-build.yml .github/workflows/build-all.yml
git commit -m "Fix build workflow: only build services with real source; disable broken apps/* template"
git push

# 2. Apply the ConfigMap and the live deployment fix
kubectl apply -f deployment-tenant-router-configmap.yaml
kubectl apply -f deployment-live.yaml

# 3. Replace the PowerShell scripts on the Windows host
copy start-tunnel.ps1 C:\Users\asadu\start-tunnel.ps1
copy watchdog.ps1 C:\Users\asadu\watchdog.ps1

# 4. Restart the tunnel using the corrected script
powershell -File C:\Users\asadu\start-tunnel.ps1

# 5. Verify
curl -I https://shopnoltd.dpdns.org
curl -I https://chat.shopnoltd.dpdns.org
```

## What's still genuinely missing (not a config fix — needs real code)

Confirmed via repo-wide search: **no source code exists anywhere** for:
- `billing-engine` (Python, port 5000 — likely Stripe integration, given
  the `stripe-secret` referenced elsewhere in the cluster)
- `oauth-service` (Node.js, port 3000 — Google/Facebook/GitHub OAuth + JWT,
  per its env vars)
- `chat`, `live` (currently running as generic `nginx:latest` placeholders
  in-cluster — not custom builds)

`tenant-router` does **not** need a custom image — it already runs
correctly as stock `openresty/openresty:alpine` plus the ConfigMap in this
package. No Dockerfile needed there.

Writing real implementations for billing-engine and oauth-service is a
separate, larger task from everything in this package — happy to start on
either once you're ready.
