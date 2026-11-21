# Shopnoltd encrypted database and Kubernetes Secrets backups

This branch contains an encrypted primary PostgreSQL dump, an encrypted
archive of every connectable non-template database plus global roles, and
the all-namespace Kubernetes Secret export. The encryption key is supplied at
runtime through BACKUP_ENCRYPTION_KEY and is never stored here.

Never publish or apply decrypted files casually. Restore is a manual,
reviewed disaster-recovery operation. GitHub Actions secret values cannot
be exported; preserve them separately in a secure password manager.
