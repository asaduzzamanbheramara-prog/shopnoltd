# Shopnoltd Database & Data Operations Control Plane

This is a release-gated platform capability. The database UI must not be considered complete merely because a generic table browser exists.

## Required capabilities

### Record operations
- Create/add, view, search, filter, sort, paginate, edit/modify, and delete.
- Bulk edit and bulk delete with explicit confirmation and permission checks.
- Draft/save/publish where an entity lifecycle requires it.
- Validation, type checking, required-field enforcement, and duplicate detection.

### Import/export
- CSV and JSON import/export for supported entities.
- XLSX export/import where spreadsheet workflows are useful.
- PDF/report generation for human-readable reports.
- Imports are size-limited, schema-validated, transactional, and fully audited; failed imports roll back rather than partially applying.

### Security and governance
- Platform-admin operations require explicit RBAC authorization.
- Tenant-scoped entities must enforce tenant isolation server-side.
- Sensitive/system tables are not writable through a generic table browser.
- No unrestricted raw SQL for normal users.
- Destructive operations require confirmation and must be audit logged.
- Backup/restore and recovery procedures must exist before destructive production workflows are enabled.

### Analysis and reporting
- Table/schema analysis, row counts, data-quality indicators, and drill-down to source records.
- Scheduled reports and exportable KPI reports.
- Audit history showing actor, operation, target entity/record, before/after state, and timestamp.
- Financial reporting must preserve Decimal/monetary precision; presentation formatting must not become the stored value.

### Visualization
The analytics layer should provide responsive HD/4K dashboards with drill-down for:

- wallet balances, ledger entries, transactions and reconciliation;
- gateway success/failure/latency and capability coverage;
- currency rates, conversions and volume;
- users, tenants and growth;
- domains, registrations and DNS activity;
- subscriptions, billing and revenue;
- AI provider/model usage and cost;
- blog/content and social activity;
- infrastructure/service health;
- database growth/activity;
- audit and security events.

Interactive 3D is reserved for genuinely spatial/network/topology data. It must remain optional and usable on responsive displays rather than becoming a decorative substitute for operational charts.

## Current implementation status

The payment-service admin table API now provides the foundation for validated table metadata, pagination/search/sort, CRUD, bulk deletion, CSV import, JSON/CSV export, table analysis, and transactional audit logging. It is intentionally a high-privilege surface.

This does **not** yet prove that every database behind every Shopnoltd service is covered. Service-specific adapters or a controlled cross-service data gateway must be added and tested for the remaining databases/entities before the platform can pass the full database-control-plane gate.

## Release gate

Do not mark the platform fully functional until the following are demonstrated in the target environment:

1. Every supported entity has the required CRUD/lifecycle operations.
2. Imports/exports validate schema and preserve data types/precision.
3. Bulk operations are permission checked, confirmed, transactional, and audited.
4. Tenant isolation is verified with cross-tenant negative tests.
5. Audit records are immutable to normal admin tooling.
6. Reports reconcile with underlying records.
7. Dashboard drill-down reaches the exact source records.
8. HD/4K visualization rendering is tested at responsive breakpoints.
9. 3D topology/relationship visualization is tested where enabled.
10. Backup/restore and disaster-recovery tests pass before destructive production operations are enabled.
