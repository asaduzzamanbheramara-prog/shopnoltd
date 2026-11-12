#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
: "${POSTGRES_NAMESPACE:=shopno-data}"
: "${POSTGRES_DEPLOYMENT:=postgres}"
: "${BACKUP_WORKDIR:=/tmp/shopnoltd-dr-backup}"
command -v kubectl >/dev/null
command -v tar >/dev/null
command -v gzip >/dev/null
command -v python3 >/dev/null
rm -rf "$BACKUP_WORKDIR"
mkdir -p "$BACKUP_WORKDIR/postgres/databases" "$BACKUP_WORKDIR/postgres/csv" "$BACKUP_WORKDIR/metadata"
pod="$(kubectl -n "$POSTGRES_NAMESPACE" get pods -l app.kubernetes.io/name=postgres -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | awk '{print $1}')"
[[ -n "$pod" ]] || { echo "No running PostgreSQL pod found" >&2; exit 1; }
kubectl -n "$POSTGRES_NAMESPACE" exec "$pod" -- sh -c '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -At -c "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
' > "$BACKUP_WORKDIR/metadata/postgres-databases.txt"
mapfile -t databases < "$BACKUP_WORKDIR/metadata/postgres-databases.txt"
(("${#databases[@]}" > 0)) || { echo "PostgreSQL returned no databases" >&2; exit 1; }
kubectl -n "$POSTGRES_NAMESPACE" exec "$pod" -- sh -c '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  exec pg_dumpall --globals-only --username="$POSTGRES_USER"
' > "$BACKUP_WORKDIR/postgres/globals.sql"
test -s "$BACKUP_WORKDIR/postgres/globals.sql"
for db in "${databases[@]}"; do
  [[ "$db" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "Unexpected database identifier; refusing export" >&2; exit 1; }
  echo "Backing up database: $db"
  kubectl -n "$POSTGRES_NAMESPACE" exec "$pod" -- sh -c '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    exec pg_dump --format=custom --no-owner --no-acl --username="$POSTGRES_USER" --dbname="$1"
  ' sh "$db" > "$BACKUP_WORKDIR/postgres/databases/$db.dump"
  test -s "$BACKUP_WORKDIR/postgres/databases/$db.dump"
  mkdir -p "$BACKUP_WORKDIR/postgres/csv/$db"
  kubectl -n "$POSTGRES_NAMESPACE" exec "$pod" -- sh -c '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -At -F "|" -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN (\047pg_catalog\047,\047information_schema\047) ORDER BY schemaname, tablename"
  ' sh "$db" > "$BACKUP_WORKDIR/metadata/$db.tables.txt"
  while IFS='|' read -r schema table; do
    [[ -n "$schema" && -n "$table" ]] || continue
    schema_sql="${schema//\"/\"\"}"
    table_sql="${table//\"/\"\"}"
    safe_schema="$(printf '%s' "$schema" | tr -c 'A-Za-z0-9_.-' '_')"
    safe_table="$(printf '%s' "$table" | tr -c 'A-Za-z0-9_.-' '_')"
    sql="COPY (SELECT * FROM \"$schema_sql\".\"$table_sql\") TO STDOUT WITH CSV HEADER"
    kubectl -n "$POSTGRES_NAMESPACE" exec "$pod" -- sh -c '
      export PGPASSWORD="$POSTGRES_PASSWORD"
      exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -c "$2"
    ' sh "$db" "$sql" > "$BACKUP_WORKDIR/postgres/csv/$db/$safe_schema--$safe_table.csv"
  done < "$BACKUP_WORKDIR/metadata/$db.tables.txt"
done
printf 'database_count=%s\n' "${#databases[@]}" > "$BACKUP_WORKDIR/metadata/summary.txt"
tar -C "$BACKUP_WORKDIR" -czf "$BACKUP_WORKDIR/postgres-all-databases.tar.gz" postgres metadata
echo "PASS: exported ${#databases[@]} PostgreSQL databases, globals, and per-table CSV files."
