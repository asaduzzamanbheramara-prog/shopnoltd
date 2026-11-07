#!/bin/sh
# Generates the LiteLLM config from the ai_providers / ai_models tables.
# - Anthropic: one deployment per API key (ANTHROPIC_API_KEY + _1.._N) => key rotation
# - "auto" group: models with is_default = true or capabilities.auto = true
# - Unknown providers are skipped with a warning instead of failing the pod
set -eu

: "${AI_DATABASE_URL:?AI_DATABASE_URL is required}"

# ai-platform stores an async SQLAlchemy URL; psql needs a plain PostgreSQL URL.
PSQL_DATABASE_URL="$(printf '%s' "$AI_DATABASE_URL" | sed 's/^postgresql+asyncpg:/postgresql:/')"
ANTHROPIC_KEY_COUNT="${ANTHROPIC_KEY_COUNT:-5}"

out=/generated/config.yaml
body=/generated/body.yaml
auto=/generated/auto.yaml
fb=/generated/fallbacks.yaml
rows_file=/generated/rows.txt
: > "$body"
: > "$auto"
: > "$fb"

psql "$PSQL_DATABASE_URL" -AtF '|' -c "
  SELECT p.name, p.provider_type::text, COALESCE(p.base_url, ''), m.model_name,
         (m.is_default OR COALESCE(m.capabilities->>'auto', '') = 'true')::text
  FROM ai_models m
  JOIN ai_providers p ON p.id = m.provider_id
  WHERE m.is_active = true
    AND p.is_active = true
  ORDER BY m.priority ASC, p.name ASC, m.model_name ASC
" > "$rows_file"

# single-quote escaping for YAML scalars
q() { printf '%s' "$1" | sed "s/'/''/g"; }

# emit <file> <alias> <upstream> <key_env> [api_base]
emit() {
  printf "  - model_name: '%s'\n    litellm_params:\n      model: '%s'\n      api_key: os.environ/%s\n" \
    "$(q "$2")" "$(q "$3")" "$4" >> "$1"
  if [ -n "${5:-}" ]; then
    printf "      api_base: '%s'\n" "$(q "$5")" >> "$1"
  fi
}

ANTHROPIC_KEYS="ANTHROPIC_API_KEY"
i=1
while [ "$i" -le "$ANTHROPIC_KEY_COUNT" ]; do
  ANTHROPIC_KEYS="$ANTHROPIC_KEYS ANTHROPIC_API_KEY_$i"
  i=$((i + 1))
done

skipped=""
while IFS='|' read -r provider ptype base_url model in_auto; do
  [ -n "$model" ] || continue
  prefix=""
  keys=""
  use_base=1
  is_anthropic=0

  case "$provider" in
    "Google Gemini") prefix="gemini/"; keys="GEMINI_API_KEY" ;;
    "Groq")          prefix="openai/"; keys="GROQ_API_KEY" ;;
    "OpenRouter")    prefix="openai/"; keys="OPENROUTER_API_KEY" ;;
    "Cerebras")      prefix="openai/"; keys="CEREBRAS_API_KEY" ;;
    *)
      case "$ptype" in
        anthropic) prefix="anthropic/"; keys="$ANTHROPIC_KEYS"; use_base=0; is_anthropic=1 ;;
        openai)    prefix="openai/"; keys="OPENAI_API_KEY"; use_base=0 ;;
        *)
          case " $skipped " in
            *" $provider "*) ;;
            *) skipped="$skipped $provider"; echo "WARN: skipping unsupported provider: $provider" >&2 ;;
          esac
          continue
          ;;
      esac
      ;;
  esac

  alias="$provider:$model"
  upstream="$prefix$model"
  base=""
  if [ "$use_base" = "1" ]; then base="$base_url"; fi

  for k in $keys; do
    emit "$body" "$alias" "$upstream" "$k" "$base"
    if [ "$in_auto" = "true" ]; then
      emit "$auto" "auto" "$upstream" "$k" "$base"
    fi
  done

  if [ "$is_anthropic" = "1" ]; then
    printf "  - '%s': ['auto']\n" "$(q "$alias")" >> "$fb"
  fi
done < "$rows_file"

body_count="$(grep -c '^  - model_name:' "$body" || true)"
auto_count="$(grep -c '^  - model_name:' "$auto" || true)"
[ "$body_count" -gt 0 ] || { echo 'ERROR: no active AI models found' >&2; exit 1; }

{
  printf '%s\n' 'model_list:'
  cat "$body"
  cat "$auto"
  printf '%s\n' '' 'router_settings:' '  routing_strategy: simple-shuffle' '  num_retries: 2' '  allowed_fails: 3' '  cooldown_time: 60' '  timeout: 120'
  if [ "$auto_count" -gt 0 ] && [ -s "$fb" ]; then
    printf '%s\n' '  fallbacks:'
    cat "$fb"
  fi
  printf '%s\n' '' 'general_settings:' '  master_key: os.environ/LITELLM_MASTER_KEY'
} > "$out"

printf 'Generated active AI model catalog: %s entries (%s in auto group)\n' "$body_count" "$auto_count"
