#!/usr/bin/env bash
set -euo pipefail

# Restore an encrypted custom-format PostgreSQL backup into the live k3s database.
# Required environment:
#   BACKUP_ENCRYPTION_KEY - same key used by the backup workflow
# Optional:
#   BACKUP_FILE - encrypted .dump.enc file (default: ./backup/latest.dump.enc)
#   POSTGRES_NAMESPACE - default: shopno-data
#   POSTGRES_DEPLOYMENT - default: postgres
#
# This is intentionally an explicit/manual recovery operation. It does not run
# automatically during normal startup because restoring production data is destructive.

BACKUP_FILE="${BACKUP_FILE:-./backup/latest.dump.enc}"
POSTGRES_NAMESPACE="${POSTGRES_NAMESPACE:-shopno-data}"
POSTGRES_DEPLOYMENT="${POSTGRES_DEPLOYMENT:-postgres}"

if [[ -z "${BACKUP_ENCRYPTION_KEY:-}" ]]; then
  echo 'ERROR: BACKUP_ENCRYPTION_KEY is required.' >&2
  exit 1
fi
if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "ERROR: backup file not found: $BACKUP_FILE" >&2
  exit 1
fi
command -v openssl >/dev/null || { echo 'ERROR: openssl is required' >&2; exit 1; }
command -v kubectl >/dev/null || { echo 'ERROR: kubectl is required' >&2; exit 1; }

umask 077
TMP_DUMP="$(mktemp /tmp/shopnoltd-restore.XXXXXX.dump)"
trap 'rm -f "$TMP_DUMP"' EXIT

echo 'Decrypting backup locally...'
echo "::add-mask::$BACKUP_ENCRYPTION_KEY"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -in "$BACKUP_FILE" -out "$TMP_DUMP" -pass env:BACKUP_ENCRYPTION_KEY

test -s "$TMP_DUMP"
kubectl -n "$POSTGRES_NAMESPACE" get deployment "$POSTGRES_DEPLOYMENT" >/dev/null

echo 'Restoring PostgreSQL database...'
kubectl -n "$POSTGRES_NAMESPACE" exec -i "deployment/$POSTGRES_DEPLOYMENT" -- \
  sh -c 'pg_restore --clean --if-exists --no-owner --no-acl --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
  < "$TMP_DUMP"

echo 'PostgreSQL restore completed.'
