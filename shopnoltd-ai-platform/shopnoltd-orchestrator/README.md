# Shopnoltd AI — Orchestration Engine

This is the working skeleton of the "fix the whole platform" loop:

```
scan repo -> build image -> push to GHCR -> patch/apply K8s manifest
    -> wait for rollout -> if unhealthy: read pod logs -> diagnose -> retry or stop
```

It replaces the placeholder `app.py` that only returned a health check.

## Files
| File | Role |
|---|---|
| `services.yaml` | Declarative list of what *should* be running — edit this first |
| `config.py` | All settings, env-var driven |
| `agents/github_agent.py` | Syncs repo, gets commit SHA for image tags |
| `agents/docker_agent.py` | Builds + pushes images to GHCR |
| `agents/k8s_agent.py` | Applies manifests, patches images, watches rollout, reads logs |
| `agents/log_analyzer.py` | Rule-based diagnosis of common pod failures |
| `agents/orchestrator.py` | The control loop tying it all together |
| `main.py` | FastAPI layer: `POST /fix`, `GET /fix/{job_id}`, `GET /logs/{deployment}` |

## Before this actually runs against your cluster

**1. Fix `services.yaml` — I guessed the Dockerfile paths.**
From your `ls` output I only confirmed these Dockerfiles exist:
- `Dockerfile` (root)
- `shopnoltd-ai-platform/backend/Dockerfile`
- `shopnoltd-ai-platform/Dockerfile`
- `ui/Dockerfile`
- `ui/admin/Dockerfile`

I mapped `api-service`, `billing-engine`, and `oauth-service` to the same
backend Dockerfile as a placeholder — check whether that's actually
correct, or whether each needs its own Dockerfile/context. If they're
genuinely separate services they likely need separate build contexts.

**2. Set these environment variables:**
```bash
export GHCR_USERNAME=your-github-username
export GHCR_TOKEN=ghp_xxx              # PAT with write:packages scope
export GHCR_NAMESPACE=your-org-or-user
export SHOPNOLTD_REPO_ROOT=/mnt/c/Users/asadu/PROJECTS/shopnoltd
export K8S_NAMESPACE=default           # or whatever namespace you use
```

**3. Docker daemon access.**
`docker_agent.py` uses `docker.from_env()`, which needs a reachable
Docker socket. Fine if you run this orchestrator on your WSL machine
directly. If you later move it *into* the cluster as its own pod, it
won't have a Docker daemon unless you mount `/var/run/docker.sock`
(works, but is a real security tradeoff) — the standard alternative is
building with **Kaniko** as a Kubernetes Job instead of `docker-py`.
That's a swap-in for `build_image()`/`push_image()`, not a rewrite of
the orchestrator.

**4. Kubernetes credentials.**
Locally it uses your kubeconfig automatically. In-cluster, set
`K8S_IN_CLUSTER=true` and give the pod a ServiceAccount with RBAC to
get/list/patch Deployments, Pods, ConfigMaps, and Services in your
namespace.

## Run it
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8080

# trigger the fix loop
curl -X POST http://localhost:8080/fix
# {"job_id": "a1b2c3d4", "status": "started"}

curl http://localhost:8080/fix/a1b2c3d4
# poll this for build/push/apply/rollout status per service,
# plus detected_issue if something is stuck
```

## What this does NOT do yet (be clear-eyed about this)
- **No LLM/RAG agent wired in.** `log_analyzer.py` is a deterministic
  rule table for known failure signatures (ImagePullBackOff, DB not
  ready, missing ConfigMap, missing migrations). Novel app-level bugs
  won't be caught by it — that's where an LLM-backed agent belongs,
  as an *additional* diagnosis path when the rule table returns
  `action="manual"`.
- **No automatic PR creation, code review, or security scanning.**
  Those are separate agents this skeleton has room for
  (`agents/pr_agent.py`, `agents/security_agent.py`) but doesn't
  implement — they're a different kind of work (talking to GitHub's
  API, static analysis tools) from the deploy-and-heal loop above.
- **No automatic rollback.** `wait_for_rollout` reports failure but
  doesn't currently call `kubectl rollout undo` equivalent. Easy to
  add to `k8s_agent.py` once you've watched it in action and are
  comfortable with it acting autonomously.
- **DB migrations are detected, not run.** `check_db` action currently
  just flags and stops — wiring in `alembic upgrade head` (or your
  migration tool) as an executed Kubernetes Job is a reasonable next
  step, not yet done, because running migrations unattended is the
  single riskiest thing in this whole loop.

## Suggested next step
Run `POST /fix` against your **actual** cluster with `MAX_RETRIES_PER_SERVICE=1`
first, read the `FixReport` it returns, and use that real output to
correct `services.yaml` and confirm the Dockerfile/context mapping
before trusting it with more retries or wider blast radius.
