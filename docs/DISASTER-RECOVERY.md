# Shopnoltd backup and automatic recovery

## Current verified backup scope

Production PostgreSQL remains on the k3s PostgreSQL PVC. Application code, Kubernetes manifests and migrations are version-controlled in the public `shopnoltd` source repository. Encrypted recovery artifacts are published to a separate private repository configured by the GitHub Actions secrets `BACKUP_REPOSITORY` and `BACKUP_REPOSITORY_TOKEN`.

The nightly/manual `.github/workflows/postgres-backup.yml` workflow currently publishes 11 backup artifacts (three encrypted data files, integrity sidecars and metadata):
- the primary PostgreSQL custom-format dump;
- an archive containing all connectable non-template databases and global roles;
- an all-namespace Kubernetes Secret export;
- SHA-256 and keyed HMAC-SHA256 integrity sidecars, timestamp and source revision metadata.

The publisher uses a normal Git clone/commit/push to the private destination and preserves prior backup history. It does not force-update the destination branch.

Verified run evidence (2026-11-25 UTC):
- Backup run [45630157073](https://github.com/asaduzzamanbheramara-prog/shopnoltd/actions/runs/45630157073): successful; encrypted artifacts published to the separate private repository.
- Isolated recovery run [45654952994](https://github.com/asaduzzamanbheramara-prog/shopnoltd/actions/runs/45654952994): successful; 35 PostgreSQL databases restored and connection-tested in disposable PostgreSQL 16; the independent primary dump was also restored.
- The same recovery run validated 100 Kubernetes Secret objects across 13 namespaces. 97 eligible application-managed Secrets were restored into a disposable kind cluster; 3 cluster-bound/controller-managed objects were intentionally excluded from that unrelated cluster. All 100 remain represented in the encrypted source archive.

These tests did not restore or modify production PostgreSQL, production Kubernetes Secrets, or production workloads.

## Explicitly uncovered recovery assets

The verified nightly workflow does **not** currently back up:
- PersistentVolume/PersistentVolumeClaim file data or volume snapshots;
- live Kubernetes ConfigMaps;
- a complete K3s control-plane state archive;
- Cloudflare tunnel credential/configuration files;
- GitHub Actions/repository/environment secret values (GitHub does not expose saved secret values for export).

Git-tracked manifests can recreate declared resources, but do not replace runtime ConfigMaps, PVC contents, uploaded files, object-store data, or credentials.

A read-only live inventory on 2026-11-25 observed 49 PVCs, all Bound. This includes PostgreSQL, MongoDB, Redis, MinIO, Keycloak, Gitea, mail, code-server, monitoring and application data claims. The matching PVs reported reclaim policy `Delete`; do not delete/recreate PVCs or PVs as part of troubleshooting or capacity work.

The live `local-path` and `standard` StorageClasses both use `rancher.io/local-path` and reported `allowVolumeExpansion=false`. Do not attempt a PVC size increase until a supported storage migration/expansion procedure is designed and verified against the actual host storage.

The current workflow's publisher artifact list contains database and Kubernetes Secret exports only. Older documentation referring to `C:\\Users\\asadu\\k3s-state-backup.tgz` and `C:\\Users\\asadu\\.cloudflared` as required inputs to that workflow was stale; those host assets must be inventoried and tested separately before they can be treated as recoverable.

## Required follow-up work

1. Design application-consistent backup/restore for every stateful PVC. Prefer native database dumps for PostgreSQL/MongoDB/Redis as appropriate, object replication for MinIO/uploads, and quiesced snapshots or application-native exports for other workloads.
2. Test restore of each stateful workload into a disposable environment. A PVC being Bound is not proof that its contents are backed up.
3. Export and compare live ConfigMap metadata/content against the deployed Git revision without exposing Secret values; identify runtime-generated ConfigMaps that need independent backup.
4. Locate and verify the current K3s server-state archive and Cloudflare tunnel files. Encrypt them and store them in the private recovery destination only after validating source age, archive contents and restore procedure.
5. Keep `BACKUP_ENCRYPTION_KEY`, `BACKUP_REPOSITORY_TOKEN` and other non-exportable GitHub secret values in an independent encrypted password manager. If a value is lost, rotate/reissue it at its source and update the GitHub secret; never put it in Git or chat.
6. Keep the isolated restore drill separate from production. Do not automatically restore during boot. Any production database, Secret, PVC or cluster recovery requires an explicit reviewed plan and approval.

## PostgreSQL capacity guard

The PostgreSQL PVC request observed in the live cluster is 10 GiB. The repository includes `ops/backup/check-postgres-storage.sh`, which checks filesystem usage and fails at the configured 80% threshold; it does not resize or recreate a PVC.

The live StorageClasses currently report `allowVolumeExpansion=false`. Do not assume a PVC patch can expand the underlying local-path volume. First design and test a safe data migration/host-capacity plan; never delete `postgres-data` to increase capacity.

## Manual recovery safety

Use the private backup repository and the isolated recovery workflow to validate a snapshot before any production recovery. A successful checksum/decryption check alone is not a restore test. The disposable restore workflow is the current reference for PostgreSQL and eligible Kubernetes Secret recovery.

A Kubernetes Secret export is not a complete cluster restore image. Restore must be deliberate and reviewed after namespaces and dependent resources are prepared; do not blindly apply an old export to a running production cluster.

## Windows/WSL recovery boundary

Starting WSL and k3s after Windows boot can recover services when the host is available. It does not provide availability while the physical PC is powered off. The K3s server-state archive, host files, PVC contents and external credentials each require their own verified backup and restore path.

## Repository and credential handling

The source repository is public; the encrypted backup destination is separately configured and verified by the backup workflow to be private. Keep encryption keys and repository tokens outside Git. GitHub Actions secret values cannot be read back after saving. Never paste tokens, private keys, Cloudflare credential files, Secret values or encryption keys into chat or workflow logs.
