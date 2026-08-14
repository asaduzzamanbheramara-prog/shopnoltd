# AI Platform — Multi-Provider Model Management (Phase 1)

Adds provider/model CRUD + activation to `ai-platform`, replacing the single
hardcoded Ollama URL with a router that can call OpenAI, Anthropic, Ollama,
Azure OpenAI, or any OpenAI-compatible endpoint — selected at runtime from
the database, not from env vars.

## What this does NOT touch
- Your existing `llm_model` / `llm_url` config fields are kept as fallback
  only — nothing currently reading them breaks.
- Doesn't change auth for other services; `require_admin` here expects the
  same JWT your other `shopno-platform` services already validate (adjust
  `app/core/security.py` if your actual decode logic differs from this
  RS256/HS256 guess — check how `gateway` currently validates tokens and
  mirror it exactly).

## 1. Files — where they go
Copy everything under `app/` into `platform/ai-platform/app/`, merging
`core/config.py` and `api/inference.py` with what's already there (they're
drop-in replacements, not separate modules). Copy `alembic/versions/...` into
your existing alembic setup, **after setting `down_revision` to your current
head** — check with `alembic current` in the ai-platform service.

## 2. New dependencies
Add to `requirements.txt` (or `pyproject.toml`) for `ai-platform`:
```
cryptography>=42.0
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29
alembic>=1.13
httpx>=0.27
```

## 3. Database
Create the `ai_platform` database on your shared Postgres if it doesn't
already exist (per your established per-service-database pattern), then run:
```
alembic upgrade head
```

## 4. Encryption key secret
```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
kubectl -n shopno-platform create secret generic ai-platform-encryption \
  --from-literal=AI_KEY_ENCRYPTION_KEY='<paste-key>'
```
Then wire it into the `ai-platform` Deployment env (see
`k8s/ai-platform-encryption-secret.yaml` for the exact snippet), and add it
to your kustomize source — not just a live patch, per your drift concerns.

## 5. Router registration
See `app/main_router_registration_snippet.py` — add those three
`include_router` calls to your existing `main.py`.

## 6. Quick usage
```bash
# Register a provider (API key encrypted at rest, never returned raw)
curl -X POST https://<gateway>/api/ai/providers \
  -H "Authorization: Bearer $ADMIN_JWT" -H "Content-Type: application/json" \
  -d '{"name":"anthropic-prod","provider_type":"anthropic","api_key":"sk-ant-...","is_active":true}'

# Register a model under that provider
curl -X POST https://<gateway>/api/ai/models/providers/<provider_id> \
  -H "Authorization: Bearer $ADMIN_JWT" -H "Content-Type: application/json" \
  -d '{"model_name":"claude-sonnet-4-6","display_name":"Claude Sonnet 4.6","is_active":true,"is_default":true}'

# Test connectivity/auth for a provider without spending tokens on a full call
curl -X POST https://<gateway>/api/ai/providers/<provider_id>/test -H "Authorization: Bearer $ADMIN_JWT"

# Run inference against whichever model is currently default/active
curl -X POST https://<gateway>/api/ai/infer \
  -H "Content-Type: application/json" -d '{"prompt":"hello"}'
```

## 7. One thing worth checking first
Your original debug session showed `kubectl get pods -l app=ai-platform`
returning **zero pods** in `shopno-platform`. Before any of this is useful,
confirm the deployment actually exists and is running:
```
kubectl -n shopno-platform get deploy,pods -l app=ai-platform
```
If it's missing entirely, that's a separate fix (deployment manifest applied?
label mismatch? different label key?) before this module has anywhere to run.

## Next phases (not built yet, per your priority order)
- **Phase 2**: Social login (Google/Facebook/GitHub) — this should be wired
  as Identity Providers inside your existing Keycloak (`shopno-identity`),
  not a custom OAuth implementation. I'll need your current Keycloak realm
  export or admin access details to scope exact steps.
- **Phase 3**: Billing/payment/exchange — since you already have a gateway
  account, next step is telling me which gateway (Stripe / SSLCommerz /
  other) so I can match their SDK and webhook signature verification
  correctly rather than guessing.
