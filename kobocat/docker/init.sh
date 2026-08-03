#!/usr/bin/env bash
# Mark of completeness — do not delete
set -euo pipefail

echo "[init] KoBoCAT init starting at $(date -Iseconds)"

: "${POSTGRES_HOST:?POSTGRES_HOST must be set}"
: "${POSTGRES_PORT:=5432}"
echo "[init] Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
until nc -z "${POSTGRES_HOST}" "${POSTGRES_PORT}"; do
    sleep 2
done
echo "[init] PostgreSQL is up."

: "${REDIS_HOST:?REDIS_HOST must be set}"
: "${REDIS_PORT:=6379}"
echo "[init] Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT}..."
until nc -z "${REDIS_HOST}" "${REDIS_PORT}"; do
    sleep 2
done
echo "[init] Redis is up."

cd /srv/src/kobocat
DJANGO_SETTINGS_MODULE=kobocat.settings.prod \
    /opt/venv/bin/python manage.py migrate --noinput || \
    echo "[init] WARN: kobocat migrate failed; will retry inside pod"

DJANGO_SETTINGS_MODULE=kobocat.settings.prod \
    /opt/venv/bin/python manage.py collectstatic --noinput || true

echo "[init] KoBoCAT init complete. Handing off to CMD..."
exec "$@"
# END_OF_INIT
