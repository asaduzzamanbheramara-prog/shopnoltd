# Disaster recovery implementation scope

The current backup covers only one PostgreSQL database and Kubernetes Secrets. A complete recovery solution must separately cover every PostgreSQL database, MongoDB, Redis, MinIO objects, PVC data, K3s bootstrap credentials, GitHub Actions secrets, and external provider credentials. Secret values must remain encrypted and must never be placed in plaintext CSV or source control. Existing snapshots must not be overwritten or deleted before a replacement is independently restored and approved.
