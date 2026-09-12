#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   cp .env.ai-providers.example .env.ai-providers.local
#   chmod +x scripts/apply-ai-provider-secrets.sh
#   scripts/apply-ai-provider-secrets.sh .env.ai-providers.local
#
# The helper never prints secret values. It patches only provider keys, so
# existing non-provider settings in ai-platform-secret are preserved.

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

echo "PASS: updated shopno-ai/litellm-provider-keys"
echo "NOTE: restart the affected deployments after changing credentials."
