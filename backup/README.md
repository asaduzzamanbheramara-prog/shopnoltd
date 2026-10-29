# Shopnoltd PostgreSQL backup

This branch contains only the latest encrypted PostgreSQL backup produced by the trusted self-hosted runner.

The encryption key is never stored in GitHub. It is supplied at runtime through the `BACKUP_ENCRYPTION_KEY` GitHub Actions secret.

Restore only through the documented recovery procedure in `docs/DISASTER-RECOVERY.md`.
