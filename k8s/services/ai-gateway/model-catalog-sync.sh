#!/bin/sh
set -eu

: "${AI_DATABASE_URL:?AI_DATABASE_URL is required}"

tmp=/generated/config.yaml
count=$(psql "$AI_DATABASE_URL" -AtF '	' -c "
  SELECT p.name, m.model_name
  FROM ai_models m
  JOIN ai_providers p ON p.id = m.provider_id
  WHERE m.is_active = true
  ORDER BY p.name, m.model_name
")

printf '%s\n' 'model_list:' > "$tmp"
n=0
printf '%s\n' "$count" | while IFS='	' read -r provider model; do
  [ -n "$model" ] || continue
  case "$provider" in
    "OpenRouter") prefix="openrouter/"; key="OPENROUTER_API_KEY" ;;
    "Google Gemini") prefix="gemini/"; key="GEMINI_API_KEY" ;;
    "Groq") prefix="groq/"; key="GROQ_API_KEY" ;;
    "Cerebras") prefix="cerebras/"; key="CEREBRAS_API_KEY" ;;
    *) continue ;;
  esac
  # Model IDs are treated as YAML single-quoted scalars; escape embedded apostrophes.
  model_q=$(printf '%s' "$model" | sed "s/'/''/g")
  upstream_q=$(printf '%s' "${prefix}${model}" | sed "s/'/''/g")
  printf "  - model_name: '%s'\n    litellm_params:\n      model: '%s'\n      api_key: os.environ/%s\n" "$model_q" "$upstream_q" "$key" >> "$tmp"
  n=$((n + 1))
done

printf '%s\n' '' 'router_settings:' '  routing_strategy: simple-shuffle' 'general_settings:' '  master_key: os.environ/LITELLM_MASTER_KEY' >> "$tmp"

models=$(grep -c '^  - model_name:' "$tmp" || true)
[ "$models" -gt 0 ] || { echo 'ERROR: no active AI models found' >&2; exit 1; }
printf 'Generated active AI model catalog: %s entries\n' "$models"
