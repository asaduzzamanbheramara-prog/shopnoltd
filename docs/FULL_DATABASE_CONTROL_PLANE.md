# Shopnoltd Full Database Control Plane

## Status

Implementation contract for the full Admin database-management requirement. This document is intentionally separate from the existing generic table browser because a browser alone is not sufficient.

## Required administrator capabilities

For every production database, the Admin control plane must expose the safe capabilities supported by that data domain:

- database/schema/table discovery
- table and column metadata
- create/read/update/delete for safe entities
- bulk create/update/delete
- replace/upsert/merge where the entity contract permits it
- table create/drop/rename
- column add/alter/rename/drop
- index inspection and controlled create/drop
- primary/foreign/unique/check constraint inspection and controlled changes
- sequence/view metadata where applicable
- CSV/JSON/XLSX import and export
- transactional import preview and rollback
- table/database analysis and data-quality checks
- PDF/CSV/XLSX reporting
- database/table growth and activity metrics
- backup and restore orchestration
- complete mutation audit trail
- tenant-aware authorization
- explicit confirmation for destructive operations

## Safety boundary

The control plane must never turn sensitive SQL state into unrestricted browser CRUD merely because a table is discoverable.

The following classes remain service-controlled unless a dedicated, validated administrative operation exists:

- wallet balances and ledger state
- payment transactions and webhook processing state
- authentication credentials and OAuth tokens
- security and audit records
- tenant/routing ownership
- infrastructure control state
- migration metadata

Financial and security mutations must use domain APIs with authorization, idempotency, locking/transaction guarantees, and audit logging.

## Adapter contract

Each database-backed service must publish a capability descriptor and server-side adapter implementing only the operations allowed for its data domain. The web portal must consume capabilities instead of hard-coding one generic database policy.

Minimum descriptor fields:

- service
- database
- schemas
- tables
- readable
- writable
- destructive
- importable
- exportable
- reportable
- ddl_capabilities
- backup_capabilities
- tenant_scope
- protected_reason

## Implementation sequence

1. Payment/billing/exchange controlled adapters and invariant-safe mutation APIs.
2. Domain/tenant/gateway adapters.
3. Identity/OAuth/audit/event protected adapters.
4. Mail/Meet/social/blog/AI/mobile/worker adapters.
5. Central backup/restore orchestration.
6. Capability-driven Admin UI.
7. Cross-service analysis/reporting and drill-down.
8. Unit, integration, RBAC, tenant-isolation, backup/restore and live k3s QA.

## Release gate

The feature is not complete until every production database has either:

- a tested service-specific administrative adapter covering its required operations, or
- an explicit read-only/protected capability descriptor with a documented reason.

A generic SQL/table browser alone does not satisfy this requirement.
