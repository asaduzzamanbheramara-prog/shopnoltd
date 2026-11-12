# Media storage manifest and GitHub archival workflow

## Status

Design proposal only. This document does not enable uploads, change production storage, or move existing objects. Implement behind a feature flag and validate in a non-production environment before rollout.

## Current architecture

The storage API uploads objects to MinIO and returns `bucket`, `key`, `size`, `sha256`, and `url`. The media service returns processed images/designs as downloads and keeps video-job files under a TTL. GitHub should store source code and small text manifests, not act as the primary binary object store for user media.

## Canonical identity and naming

For every accepted object, generate a server-side UUID and UTC timestamp. Never trust a client-supplied ID, path, or timestamp.

- `Name_ID_Link_Date_Time` is a display/manifest convention, not a filesystem path supplied by the client.
- Suggested safe object key: `media/{tenant-id}/{YYYY}/{MM}/{uuid}/{sanitized-name}.{ext}`.
- Manifest record fields: `id`, `original_name`, `object_key`, `url`, `created_at_utc`, `size_bytes`, `content_type`, `sha256`, `visibility`, `tenant_id`, and `storage_provider`.
- Do not include access tokens, credentials, private user data, or sensitive filenames in GitHub paths, commit messages, or public manifests.
- Public URLs must be genuinely public URLs; do not put short-lived presigned URLs into durable manifests.

## Upload and verification flow

1. Authenticate the user and authorize tenant/object ownership.
2. Enforce allowlisted content types, maximum size, filename sanitization, and streaming upload limits.
3. Generate the UUID and UTC timestamp on the server; compute SHA-256 while streaming bytes.
4. Store binary content in MinIO/object storage. Do not put large binaries in the Git repository.
5. Read back the stored object (or use a trusted storage checksum when its semantics are documented) and verify size and SHA-256 before marking the record verified.
6. Persist the metadata record in the application database. Return the ID, canonical URL, timestamp, and SHA-256.
7. Optionally enqueue a redacted JSONL/CSV manifest event for private GitHub archival. The event must contain metadata only, never the binary, credentials, or user-private content.
8. Retry archival idempotently using the object ID; do not create duplicate manifest entries after retries.
9. If archival fails, keep the object and database record intact and report archival status separately. Never delete the only copy because a GitHub upload failed.

## GitHub archival constraints

- Use a dedicated private repository and a least-privilege GitHub App/token stored only in Kubernetes Secrets or a secret manager.
- Keep the token out of source code, ConfigMaps, logs, URLs, and manifest records.
- Upload only small, non-sensitive metadata manifests to GitHub. GitHub repository contents API is not a suitable large-media upload service; use MinIO or object storage for images/videos and larger files.
- Avoid committing binary media or frequently changing large manifests into the application repository.
- Set retention, access, and deletion policies before enabling archival; honor user deletion and legal/privacy requirements.
- Do not use GitHub commit history as the only backup for production database records or secrets.

## Acceptance tests required before rollout

- Names with Unicode, path traversal, control characters, and reserved characters cannot escape the generated storage prefix.
- UUID uniqueness and UTC timestamps are deterministic in format and generated server-side.
- SHA-256 matches a known test vector and a read-back copy; tampered bytes fail verification.
- A tenant cannot access or archive another tenant's object.
- Oversized, empty, malformed, or disallowed uploads are rejected without orphaned partial objects.
- GitHub outage/rate limit does not lose uploads; retry is idempotent and observable.
- Private object URLs are never published to a public manifest; expiring signed URLs are never treated as permanent links.
- Existing API response fields and upload paths remain backward compatible.
- Production rollout is feature-flagged, metrics/alerts exist, and rollback is tested.

## Storage cleanup safety

Do not delete local files, MinIO objects, database rows, backups, or Kubernetes state as part of this feature. Cleanup requires a separate inventory, confirmed remote copy, checksum verification, tested restore, and explicit approval.
