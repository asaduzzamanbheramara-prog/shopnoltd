# Shopnoltd disaster-recovery backup

## Included by the proposed full-backup workflow

- Every non-template PostgreSQL database discovered from the live catalog, each as a custom-format dump.
- PostgreSQL global roles and grants.
- One CSV file per application table. These CSVs are inside the encrypted archive; do not publish them separately.
- MongoDB all-database mongodump archive, including its database contents.
- Redis RDB snapshot transferred with redis-cli --rdb (replication transfer; no SAVE/BGSAVE command).
- MinIO local-path PVC contents, but only while the MinIO Deployment is confirmed scaled to zero. The job fails closed if MinIO is active or the PV path is not accessible.
- K3s server token and available local K3s kubeconfig/config files. The self-hosted runner must have non-interactive sudo read access; otherwise the job fails closed.
- All-namespace Kubernetes Secret JSON, including Secret data values. The JSON is encrypted separately; Secret values are never written to plaintext CSV.
- PVC inventory metadata for recovery planning.

The complete data archive and Kubernetes Secret export are encrypted before publication. The workflow derives an HMAC key from the externally supplied backup passphrase and verifies both HMAC and SHA-256 before publishing. The encryption passphrase is not stored in this repository.

## Runner storage

The helper requires at least 20 GiB free staging space by default. Set the repository variable BACKUP_WORKDIR to an approved Linux path such as /mnt/d/shopnoltd-dr-backup if the default WSL /tmp filesystem is too small. The path must end in shopnoltd-dr-backup. The backup job must not be run on a nearly full system disk.

## Recovery key and actual credential values

Kubernetes Secret values and the K3s server token are captured in encrypted archives. Keep the exact BACKUP_ENCRYPTION_KEY in an independent password manager and a separately protected offline recovery copy. A backup without that exact key cannot be decrypted.

GitHub Actions repository/environment secrets are write-only: GitHub does not return their existing values. Cloudflare, registrar, payment, mail, OAuth and other external-provider credentials are not automatically recoverable from GitHub. Preserve their actual values in an approved password manager when provisioned; if a value was never escrowed, reissue it with the provider. Never put these values in Git, logs, chat, or plaintext CSV.

## Still not covered / not yet proven

- Other application PVC contents (for example Gitea, n8n, mail, Keycloak, code-server, Grafana, Prometheus, Loki, and service-specific volumes) are inventoried but not copied by this workflow.
- External provider credentials and GitHub Actions secret values require independent vault escrow or provider reissue.
- A successful encryption/decryption check is not a full restore test. PostgreSQL, MongoDB, Redis, MinIO, K3s bootstrap and Kubernetes Secret restore procedures each need isolated restore tests before production replacement or cleanup.
- This PR does not itself run a production backup, restore, deploy, rotate credentials, or apply Kubernetes Secrets.

## Snapshot safety

Each successful run appends a UTC-timestamped directory to the database-backups branch. The workflow does not force-push or automatically delete prior snapshots. Retention cleanup must be a separately reviewed operation after restore verification and explicit approval.
