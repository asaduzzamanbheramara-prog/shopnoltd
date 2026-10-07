#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   cp .env.ai-providers.example .env.ai-providers.local
#   chmod +x scripts/apply-ai-provider-secrets.sh
#   scripts/apply-ai-provider-secrets.sh .env.ai-providers.local
#
# The helper never prints secret values. It patches only provider keys and the
# dedicated runtime secrets needed by LiteLLM and Code Server.

ENV_FILE="${1:-.env.ai-providers.local}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: missing $ENV_FILE" >&2
  echo "Copy .env.ai-providers.example to .env.ai-providers.local and fill it locally." >&2
  exit 1
fi

command -v kubectl >/dev/null || { echo "ERROR: kubectl is required" >&2; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: python3 is required" >&2; exit 1; }

PATCH_JSON="$(python3 - "$ENV_FILE" <<'PY'
import base64
import json
import sys

path = sys.argv[1]
allowed = {
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "MISTRAL_API_KEY",
    "GROQ_API_KEY", "DEEPSEEK_API_KEY", "XAI_API_KEY", "COHERE_API_KEY",
    "OPENROUTER_API_KEY", "TOGETHERAI_API_KEY", "FIREWORKS_API_KEY",
    "PERPLEXITY_API_KEY", "CEREBRAS_API_KEY", "AI21_API_KEY",
    "SAMBANOVA_API_KEY", "REPLICATE_API_TOKEN", "HUGGINGFACE_API_KEY",
    "LITELLM_MASTER_KEY",
}
values = {}
for raw in open(path, encoding="utf-8"):
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if key in allowed and value:
        values[key] = base64.b64encode(value.encode()).decode()
print(json.dumps({"data": values}, separators=(",", ":")))
PY
)"

if [[ "$PATCH_JSON" == '{"data":{}}' ]]; then
  echo "ERROR: no non-empty provider credentials found in $ENV_FILE" >&2
  exit 1
fi

# Patch the application secret if it already exists; do not replace unrelated
# database/Redis/auth settings stored in that Secret.
if kubectl -n shopno-platform get secret ai-platform-secret >/dev/null 2>&1; then
  kubectl -n shopno-platform patch secret ai-platform-secret --type merge -p "$PATCH_JSON" >/dev/null
  echo "PASS: patched shopno-platform/ai-platform-secret"
else
  echo "ERROR: shopno-platform/ai-platform-secret does not exist; refusing to create an incomplete application secret." >&2
  exit 1
fi

# LiteLLM uses the same provider-key names. Create/update only this dedicated
# secret; blank entries are never written.
if kubectl -n shopno-ai get secret litellm-provider-keys >/dev/null 2>&1; then
  kubectl -n shopno-ai patch secret litellm-provider-keys --type merge -p "$PATCH_JSON" >/dev/null
else
  kubectl -n shopno-ai create secret generic litellm-provider-keys \
    --from-env-file="$ENV_FILE" >/dev/null
fi

# The catalog sync init container also needs the AI Platform database URL.
# Copy only that one existing secret key into the dedicated LiteLLM namespace;
# never print the value and never overwrite unrelated LiteLLM credentials.
AI_DATABASE_URL_B64="$(kubectl -n shopno-platform get secret ai-platform-secret -o jsonpath='{.data.DATABASE_URL}')"
if [[ -z "$AI_DATABASE_URL_B64" ]]; then
  echo "ERROR: shopno-platform/ai-platform-secret has no DATABASE_URL; refusing to create an unusable catalog sync." >&2
  exit 1
fi
DB_PATCH_JSON="$(python3 - "$AI_DATABASE_URL_B64" <<'PY'
import base64, json, sys
value = sys.argv[1]
base64.b64decode(value).decode()
print(json.dumps({"data": {"DATABASE_URL": value}}, separators=(",", ":")))
PY
)"
kubectl -n shopno-ai patch secret litellm-provider-keys --type merge -p "$DB_PATCH_JSON" >/dev/null
echo "PASS: synchronized AI database URL to shopno-ai/litellm-provider-keys"
# LiteLLM's catalog sync init container needs the AI platform database URL.
# Copy only that existing value into the dedicated LiteLLM secret; never print it.
AI_DB_B64="$(kubectl -n shopno-platform get secret ai-platform-secret -o jsonpath='{.data.DATABASE_URL}')"
if [[ -z "$AI_DB_B64" ]]; then
  echo "ERROR: ai-platform-secret/DATABASE_URL is missing" >&2
  exit 1
fi
kubectl -n shopno-ai patch secret litellm-provider-keys --type merge \
  -p "{\"data\":{\"DATABASE_URL\":\"$AI_DB_B64\"}}" >/dev/null
echo "PASS: synchronized LiteLLM DATABASE_URL"

# Code Server runs in a different namespace, so it cannot reference the
# shopno-ai Secret directly. Keep a namespace-local Secret containing only the
# LiteLLM master key required by Continue.
MASTER_KEY_B64="$(python3 - "$PATCH_JSON" <<'PY'
import json, sys
data = json.loads(sys.argv[1]).get("data", {})
value = data.get("LITELLM_MASTER_KEY", "")
if not value:
    raise SystemExit("ERROR: LITELLM_MASTER_KEY is required for Code Server")
print(value)
PY
)"
if kubectl -n shopno-apps get secret code-server-litellm-key >/dev/null 2>&1; then
  kubectl -n shopno-apps patch secret code-server-litellm-key --type merge \
    -p "{\"data\":{\"LITELLM_MASTER_KEY\":\"$MASTER_KEY_B64\"}}" >/dev/null
else
  kubectl -n shopno-apps create secret generic code-server-litellm-key \
    --from-literal="LITELLM_MASTER_KEY=$(printf '%s' "$MASTER_KEY_B64" | base64 -d)" >/dev/null
fi
echo "PASS: synchronized shopno-apps/code-server-litellm-key"

echo "NOTE: restart the affected deployments after changing credentials."
