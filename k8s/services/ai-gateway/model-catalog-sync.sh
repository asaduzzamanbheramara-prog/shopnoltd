#!/bin/sh
set -eu

: "${AI_DATABASE_URL:?AI_DATABASE_URL is required}"

tmp=/generated/config.yaml
rows="$(psql "$AI_DATABASE_URL" -AtF '	' -c "
  SELECT p.name, p.provider_type::text, COALESCE(p.base_url, ''), m.model_name
  FROM ai_models m
  JOIN ai_providers p ON p.id = m.provider_id
  WHERE m.is_active = true
    AND p.is_active = true
  ORDER BY m.priority ASC, p.name ASC, m.model_name ASC
")"

printf '%s\n' 'model_list:' > "$tmp"
models=0

printf '%s\n' "$rows" | while IFS='	' read -r provider provider_type base_url model; do
  [ -n "$model" ] || continue

  case "$provider" in
    "Google Gemini")
      upstream_prefix="gemini/"
      key="GEMINI_API_KEY"
      ;;
    "Groq")
      upstream_prefix="openai/"
      key="GROQ_API_KEY"
      ;;
    "OpenRouter")
      upstream_prefix="openai/"
      key="OPENROUTER_API_KEY"
      ;;
    "Cerebras")
      upstream_prefix="openai/"
      key="CEREBRAS_API_KEY"
      ;;
    *)
      echo "ERROR: unsupported active AI provider: $provider" >&2
      exit 1
      ;;
  esac

  # Keep every provider/model deployment separately discoverable in LiteLLM.
  # YAML single-quoted scalars do not require backslash escaping for ':' or '/'. Keep
  # the provider/model alias literal so LiteLLM exposes the exact catalog identity.
  alias="$(printf '%s:%s' "$provider" "$model")"
  alias_q="$(printf '%s' "$alias" | sed "s/'/''/g")"
  upstream_q="$(printf '%s%s' "$upstream_prefix" "$model" | sed "s/'/''/g")"

  printf "  - model_name: '%s'\n    litellm_params:\n      model: '%s'\n      api_key: os.environ/%s\n"     "$alias_q" "$upstream_q" "$key" >> "$tmp"

  if [ -n "$base_url" ]; then
    base_q="$(printf '%s' "$base_url" | sed "s/'/''/g")"
    printf "      api_base: '%s'\n" "$base_q" >> "$tmp"
  fi

  models=$((models + 1))
done

printf '%s\n' '' 'router_settings:' '  routing_strategy: simple-shuffle' 'general_settings:' '  master_key: os.environ/LITELLM_MASTER_KEY' >> "$tmp"

count="$(grep -c '^  - model_name:' "$tmp" || true)"
[ "$count" -gt 0 ] || { echo 'ERROR: no active AI models found' >&2; exit 1; }
printf 'Generated active AI model catalog: %s entries\n' "$count"
