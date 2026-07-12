#!/bin/bash
set -e
# Parses host/port out of DATABASE_URL, e.g. postgres://user:pass@host:5432/db
DB_HOST=$(echo "$DATABASE_URL" | sed -E 's#.*://[^@]*@([^:/]+).*#\1#')
DB_PORT=$(echo "$DATABASE_URL" | sed -E 's#.*:([0-9]+)/.*#\1#')
DB_PORT="${DB_PORT:-5432}"
echo "Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
for i in $(seq 1 60); do
  if (echo > /dev/tcp/${DB_HOST}/${DB_PORT}) >/dev/null 2>&1; then
    echo "Postgres is up."
    exit 0
  fi
  sleep 2
done
echo "Timed out waiting for Postgres at ${DB_HOST}:${DB_PORT}."
exit 1
