#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
: "${POSTGRES_NAMESPACE:=shopno-data}"
: "${POSTGRES_DEPLOYMENT:=postgres}"
: "${BACKUP_WORKDIR:=/tmp/shopnoltd-dr-backup}"
: "${DATA_NAMESPACE:=shopno-data}"
: "${MIN_BACKUP_FREE_KB:=20971520}"
case "$BACKUP_WORKDIR" in /tmp/shopnoltd-dr-backup|/mnt/*/shopnoltd-dr-backup) ;; *) echo "Unsafe BACKUP_WORKDIR path" >&2; exit 1 ;; esac
for cmd in kubectl tar gzip python3 sudo df; do command -v "$cmd" >/dev/null; done
mkdir -p "$(dirname "$BACKUP_WORKDIR")"
available_kb="$(df -Pk "$(dirname "$BACKUP_WORKDIR")" | awk 'NR==2 {print $4}')"
[[ "$available_kb" =~ ^[0-9]+$ ]] && (( available_kb >= MIN_BACKUP_FREE_KB )) || {
  echo "Insufficient free space for safe backup staging: need at least ${MIN_BACKUP_FREE_KB} KiB, have ${available_kb:-unknown} KiB. Set BACKUP_WORKDIR to an approved external volume." >&2
  exit 1
}
rm -rf "$BACKUP_WORKDIR"
mkdir -p "$BACKUP_WORKDIR/postgres/databases" "$BACKUP_WORKDIR/postgres/csv" "$BACKUP_WORKDIR/mongodb" "$BACKUP_WORKDIR/redis" "$BACKUP_WORKDIR/minio" "$BACKUP_WORKDIR/k3s" "$BACKUP_WORKDIR/metadata"

pg_pod="$(kubectl -n "$POSTGRES_NAMESPACE" get pods -l app.kubernetes.io/name=postgres -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | awk '{print $1}')"
[[ -n "$pg_pod" ]] || { echo "No running PostgreSQL pod found" >&2; exit 1; }
kubectl -n "$POSTGRES_NAMESPACE" exec "$pg_pod" -- sh -c '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -At -c "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
' > "$BACKUP_WORKDIR/metadata/postgres-databases.txt"
mapfile -t databases < "$BACKUP_WORKDIR/metadata/postgres-databases.txt"
(("${#databases[@]}" > 0)) || { echo "PostgreSQL returned no databases" >&2; exit 1; }
kubectl -n "$POSTGRES_NAMESPACE" exec "$pg_pod" -- sh -c '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  exec pg_dumpall --globals-only --username="$POSTGRES_USER"
' > "$BACKUP_WORKDIR/postgres/globals.sql"
test -s "$BACKUP_WORKDIR/postgres/globals.sql"
for db in "${databases[@]}"; do
  [[ "$db" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "Unexpected database identifier; refusing export" >&2; exit 1; }
  echo "Backing up PostgreSQL database: $db"
  kubectl -n "$POSTGRES_NAMESPACE" exec "$pg_pod" -- sh -c '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    exec pg_dump --format=custom --no-owner --no-acl --username="$POSTGRES_USER" --dbname="$1"
  ' sh "$db" > "$BACKUP_WORKDIR/postgres/databases/$db.dump"
  test -s "$BACKUP_WORKDIR/postgres/databases/$db.dump"
  mkdir -p "$BACKUP_WORKDIR/postgres/csv/$db"
  kubectl -n "$POSTGRES_NAMESPACE" exec "$pg_pod" -- sh -c '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -At -F "|" -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN (\$\$pg_catalog\$\$,\$\$information_schema\$\$) ORDER BY schemaname, tablename"
  ' sh "$db" > "$BACKUP_WORKDIR/metadata/$db.tables.txt"
  while IFS='|' read -r schema table; do
    [[ -n "$schema" && -n "$table" ]] || continue
    schema_sql="${schema//\"/\"\"}"
    table_sql="${table//\"/\"\"}"
    safe_schema="$(printf '%s' "$schema" | tr -c 'A-Za-z0-9_.-' '_')"
    safe_table="$(printf '%s' "$table" | tr -c 'A-Za-z0-9_.-' '_')"
    sql="COPY (SELECT * FROM \"$schema_sql\".\"$table_sql\") TO STDOUT WITH CSV HEADER"
    kubectl -n "$POSTGRES_NAMESPACE" exec "$pg_pod" -- sh -c '
      export PGPASSWORD="$POSTGRES_PASSWORD"
      exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -c "$2"
    ' sh "$db" "$sql" > "$BACKUP_WORKDIR/postgres/csv/$db/$safe_schema--$safe_table.csv"
  done < "$BACKUP_WORKDIR/metadata/$db.tables.txt"
done

mongo_pod="$(kubectl -n "$DATA_NAMESPACE" get pods -l app=mongo -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | awk '{print $1}')"
[[ -n "$mongo_pod" ]] || { echo "No running MongoDB pod found" >&2; exit 1; }
kubectl -n "$DATA_NAMESPACE" exec "$mongo_pod" -- sh -c '
  command -v mongodump >/dev/null
  exec mongodump --host 127.0.0.1 --port 27017 --username="$MONGO_INITDB_ROOT_USERNAME" --password="$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase=admin --archive --gzip
' > "$BACKUP_WORKDIR/mongodb/all-databases.archive.gz"
test -s "$BACKUP_WORKDIR/mongodb/all-databases.archive.gz"

redis_pod="$(kubectl -n "$DATA_NAMESPACE" get pods -l app.kubernetes.io/name=redis -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | awk '{print $1}')"
[[ -n "$redis_pod" ]] || { echo "No running Redis pod found" >&2; exit 1; }
kubectl -n "$DATA_NAMESPACE" exec "$redis_pod" -- sh -c '
  set -e
  trap "rm -f /tmp/shopnoltd-redis-backup.rdb" EXIT
  export REDISCLI_AUTH="$REDIS_PASSWORD"
  redis-cli --rdb /tmp/shopnoltd-redis-backup.rdb
  test -s /tmp/shopnoltd-redis-backup.rdb
  cat /tmp/shopnoltd-redis-backup.rdb
' > "$BACKUP_WORKDIR/redis/dump.rdb"
test -s "$BACKUP_WORKDIR/redis/dump.rdb"

# MinIO is scaled to zero. Mount its local-path PVC read-only in a short-lived
# helper pod on the PV's node; do not read hostPath files with sudo.
minio_replicas="$(kubectl -n "$DATA_NAMESPACE" get deployment minio -o jsonpath='{.spec.replicas}')"
[[ "$minio_replicas" == "0" ]] || { echo "MinIO is active; refusing a non-atomic PVC copy." >&2; exit 1; }
minio_pvc_volume="$(kubectl -n "$DATA_NAMESPACE" get pvc minio-data -o jsonpath='{.spec.volumeName}')"
[[ -n "$minio_pvc_volume" ]] || { echo "MinIO PVC is not bound" >&2; exit 1; }
minio_node="$(kubectl get pv "$minio_pvc_volume" -o jsonpath='{.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0]}')"
[[ -n "$minio_node" ]] || { echo "MinIO PV node affinity is unavailable" >&2; exit 1; }
minio_reader="shopnoltd-minio-backup-${GITHUB_RUN_ID:-manual}"
cat > "$BACKUP_WORKDIR/minio/reader-pod.yaml" <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: $minio_reader
  namespace: $DATA_NAMESPACE
spec:
  nodeName: $minio_node
  restartPolicy: Never
  automountServiceAccountToken: false
  securityContext:
    runAsUser: 10001
    runAsGroup: 10001
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: reader
      image: busybox:1.36
      command: ["sh", "-c", "sleep 180"]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
      volumeMounts:
        - name: minio-data
          mountPath: /data
          readOnly: true
  volumes:
    - name: minio-data
      persistentVolumeClaim:
        claimName: minio-data
EOF
cleanup_minio_reader() { kubectl -n "$DATA_NAMESPACE" delete pod "$minio_reader" --ignore-not-found --wait=false >/dev/null 2>&1 || true; }
trap cleanup_minio_reader EXIT
kubectl apply -f "$BACKUP_WORKDIR/minio/reader-pod.yaml"
kubectl -n "$DATA_NAMESPACE" wait --for=condition=Ready "pod/$minio_reader" --timeout=180s
kubectl -n "$DATA_NAMESPACE" exec "$minio_reader" -- tar -C /data -czf - . > "$BACKUP_WORKDIR/minio/minio-pvc.tar.gz"
test -s "$BACKUP_WORKDIR/minio/minio-pvc.tar.gz"
kubectl -n "$DATA_NAMESPACE" delete pod "$minio_reader" --wait=true
trap - EXIT

# K3s bootstrap token is host-only and must be made readable to the runner via
# a narrowly scoped, reviewed sudoers rule; never print it in logs.
sudo -n test -r /var/lib/rancher/k3s/server/token || { echo "Backup runner lacks non-interactive read access to the K3s server token." >&2; exit 1; }
sudo -n cat /var/lib/rancher/k3s/server/token > "$BACKUP_WORKDIR/k3s/server-token"
if sudo -n test -r /etc/rancher/k3s/k3s.yaml; then sudo -n cat /etc/rancher/k3s/k3s.yaml > "$BACKUP_WORKDIR/k3s/k3s.yaml"; fi
if sudo -n test -r /etc/rancher/k3s/config.yaml; then sudo -n cat /etc/rancher/k3s/config.yaml > "$BACKUP_WORKDIR/k3s/config.yaml"; fi
test -s "$BACKUP_WORKDIR/k3s/server-token"

kubectl get pvc --all-namespaces -o json > "$BACKUP_WORKDIR/metadata/pvc-inventory.json"
python3 - "$BACKUP_WORKDIR/metadata/pvc-inventory.json" "$BACKUP_WORKDIR/metadata/pvc-inventory.txt" <<'PY'
import json, sys
doc=json.load(open(sys.argv[1], encoding="utf-8"))
with open(sys.argv[2], "w", encoding="utf-8") as out:
    for x in sorted(doc.get("items", []), key=lambda v:(v["metadata"]["namespace"],v["metadata"]["name"])):
        m=x["metadata"]; s=x.get("status",{})
        out.write(f'{m["namespace"]}/{m["name"]}|{s.get("phase","unknown")}|{s.get("capacity",{}).get("storage","unknown")}\n')
PY
printf 'postgres_database_count=%s\n' "${#databases[@]}" > "$BACKUP_WORKDIR/metadata/summary.txt"
printf '%s\n' "MongoDB archive, Redis RDB, MinIO PVC archive, and K3s bootstrap files included." > "$BACKUP_WORKDIR/metadata/other-stores.txt"
tar -C "$BACKUP_WORKDIR" -czf "$BACKUP_WORKDIR/postgres-all-databases.tar.gz" postgres mongodb redis minio k3s metadata
echo "PASS: PostgreSQL databases and CSV, MongoDB, Redis, MinIO PVC and K3s bootstrap files staged."
