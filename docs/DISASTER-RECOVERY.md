# Shopnoltd backup and automatic recovery

## Database model

Production PostgreSQL data remains on the k3s PostgreSQL PVC. GitHub is the source of truth for application code, Kubernetes manifests and migrations. The `database-backups` branch is a separate recovery copy containing only the latest **encrypted** PostgreSQL custom-format dump.

The live database is never committed to `main`, and plaintext SQL/dump files are excluded by `.gitignore`.

## Database storage capacity

The current PostgreSQL PVC request is **10 GiB**. That is a reasonable starting capacity, but it is tight for the full Shopnoltd platform because database growth can come from users/authentication, domains, billing/payment/wallet ledgers, work/evidence records, social/chat/messaging, AI/provider usage, CMS/blog data and audit/event records.

Do not delete or recreate `postgres-data` to increase capacity. First verify that the live `standard` StorageClass supports volume expansion, then perform a controlled PVC expansion. A practical next capacity target is **20 GiB or larger**, based on measured usage and the available host disk; do not blindly resize until the live storage backend is confirmed expandable.

The repository now includes `ops/backup/check-postgres-storage.sh` and `.github/workflows/postgres-storage-check.yml`. The check fails when the PostgreSQL filesystem reaches 80% usage so capacity can be expanded before exhaustion. The guard does not resize or recreate the PVC.

Extra host storage is also useful for the overall platform because PostgreSQL, OpenSearch, MinIO, Redis and other stateful workloads share the k3s node. Backup working files are temporary and are removed after the encrypted backup completes, so they should not be treated as PostgreSQL data capacity.

## Required environment/secret

Create the GitHub Actions repository secret:

- `BACKUP_ENCRYPTION_KEY` — a long, randomly generated encryption password kept outside Git.

The workflow passes it to the backup process through the environment. It is never written to a repository file. The Kubernetes PostgreSQL password is read only at runtime from `shopno-data/postgres-secret` and is not printed.

A local environment can follow `ops/backup/backup.env.example`, but the real `.env` must remain outside Git.

## Automatic backup

`.github/workflows/postgres-backup.yml` runs nightly on the trusted self-hosted k3s runner and can also be started manually. It:

1. verifies the runner and Kubernetes connection;
2. runs `pg_dump` inside the PostgreSQL container;
3. encrypts the custom-format dump with OpenSSL AES-256-CBC + PBKDF2;
4. verifies the encrypted file checksum;
5. decrypts it as an integrity test without restoring it;
6. force-updates the `database-backups` branch so GitHub keeps the latest encrypted snapshot;
7. removes plaintext and temporary backup material from the runner.

The backup branch is deliberately single-snapshot to prevent unbounded Git history growth. For longer historical retention, use an external object-storage backup in addition to this GitHub recovery copy. The encrypted GitHub copy is a recovery layer, not a replacement for capacity planning or an independent backup target.

## Manual restore

Do not restore automatically during boot. A database restore is destructive and must be explicitly started.

After checking out the `database-backups` branch, set `BACKUP_ENCRYPTION_KEY` in the environment and run:

```bash
BACKUP_ENCRYPTION_KEY='...' ./ops/backup/restore-postgres.sh
```

The script decrypts the backup locally and streams it to `pg_restore` inside the trusted PostgreSQL pod. It never commits the decrypted database to Git.

## Windows reboot recovery

Run `ops/windows/install-shopnoltd-autostart.ps1` once from an elevated PowerShell prompt on the Windows host. It creates a Windows Scheduled Task that starts the configured WSL distribution at Windows boot.

Inside WSL, systemd must be enabled and the following services must be enabled:

```bash
sudo systemctl enable k3s
sudo systemctl enable actions.runner.*.service
```

The existing `ops/github-runner/bootstrap-k3s-runner.sh` installs the GitHub runner as a system service. It requires a short-lived `RUNNER_TOKEN` only during initial registration and does not store that token in Git.

Normal recovery chain:

```text
Windows boot
  -> WSL starts
  -> WSL systemd
  -> k3s
  -> PostgreSQL PVC
  -> ArgoCD
  -> GitHub main reconciliation
  -> Kubernetes services
  -> Cloudflared
  -> Cloudflare
  -> public Shopnoltd services
```

This makes a normal PC/Windows reboot self-recovering. It does not provide availability while the physical PC is completely powered off; for that, production must eventually run on an always-on node or external cluster.

## Verification checklist

After installation, verify:

```bash
systemctl is-enabled k3s
systemctl is-active k3s
systemctl list-units 'actions.runner.*.service' --all
kubectl get nodes
kubectl -n argocd get application shopnoltd
bash ops/backup/check-postgres-storage.sh
```

Then run the normal public smoke/release gates. A successful backup workflow alone does not prove that the public website is healthy.
